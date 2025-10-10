# Comp_measured_phits_v10.py
import pandas as pd
import numpy as np
import os
import sys
from io import StringIO
import re
from textwrap import dedent
import argparse
import configparser

try:
    import matplotlib.pyplot as plt
    import pymedphys
    from scipy.signal import savgol_filter
except ModuleNotFoundError as e:
    print(f"エラー: 必要なライブラリがインストールされていません - {e}", file=sys.stderr)
    print("次のコマンドでインストールしてください: pip install pandas numpy matplotlib scipy pymedphys", file=sys.stderr)
    sys.exit(1)

__version__ = "10.0.AXIS_SELECT"

def load_measured_data(file_path):
    """実測データCSVファイルを読み込む"""
    try:
        header_row_index = 0
        axis_from_header = None
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            for i, line in enumerate(f):
                if '(cm)' in line and ',' in line:
                    header_row_index = i
                    match = re.match(r'^"?([XYZ])\s*\(', line.strip(), re.IGNORECASE)
                    if match:
                        axis_from_header = match.group(1).lower()
                    break
        df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=header_row_index)
        # 列数が2でない場合のエラーハンドリングを追加
        if len(df.columns) != 2:
             print(f"エラー: {file_path} の列数が2ではありません。形式を確認してください。", file=sys.stderr)
             # 不要な列を削除し、最初の2列のみを使用する試み
             df = df.iloc[:, :2]
             print("警告: 最初の2列のみを使用して処理を続行します。")
        
        df.columns = ['pos', 'dose']
        df['pos'] = pd.to_numeric(df['pos'], errors='coerce')
        df['dose'] = pd.to_numeric(df['dose'], errors='coerce')
        df.dropna(inplace=True)
        if df.empty:
            print(f"エラー: {file_path} 内に有効な数値データが見つかりませんでした。", file=sys.stderr)
            return None, None
        df['dose_normalized'] = (df['dose'] / df['dose'].max()) * 100
        print(f"✅ 実測データを読み込みました。(プロファイル軸: {axis_from_header or '不明'})")
        return df, axis_from_header
    except FileNotFoundError:
        print(f"エラー: 実測データファイルが見つかりません: {file_path}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"エラー: 実測データの読み込み中に問題が発生しました - {e}", file=sys.stderr)
        return None, None

def parse_phits_3d_tally(file_path):
    """PHITSの3Dメッシュタリー(t-deposit)を読み込む"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        last_tally_start_index = next((i for i in range(len(lines) - 1, -1, -1) if '[ T-Deposit ]' in lines[i]), -1)
        if last_tally_start_index == -1:
            print(f"エラー: {file_path} 内に [ T-Deposit ] タリーが見つかりません。", file=sys.stderr)
            return None

        header_lines = lines[last_tally_start_index:]
        params = {}
        data_start_index = -1
        
        for i, line in enumerate(header_lines):
            sline = line.strip()
            if sline.startswith('nx ='): params['nx'] = int(sline.split('=')[1].split('#')[0].strip())
            if sline.startswith('ny ='): params['ny'] = int(sline.split('=')[1].split('#')[0].strip())
            if sline.startswith('nz ='): params['nz'] = int(sline.split('=')[1].split('#')[0].strip())
            if sline.startswith('x ='):
                parts = sline.split('=')[1].split('#')[0].strip().split()
                params['x'] = np.linspace(float(parts[0]), float(parts[1]), params['nx'])
            if sline.startswith('y ='):
                parts = sline.split('=')[1].split('#')[0].strip().split()
                params['y'] = np.linspace(float(parts[0]), float(parts[1]), params['ny'])
            if sline.startswith('z ='):
                parts = sline.split('=')[1].split('#')[0].strip().split()
                params['z'] = np.linspace(float(parts[0]), float(parts[1]), params['nz'])
            if sline.startswith('#') and 'x' in sline and 'y' in sline and 'z' in sline:
                # Find the actual start of data, skipping blank lines and comments
                actual_data_idx = last_tally_start_index + i + 1
                while actual_data_idx < len(lines) and (lines[actual_data_idx].strip() == "" or lines[actual_data_idx].strip().startswith('#')):
                    actual_data_idx += 1
                data_start_index = actual_data_idx
                break
        
        if not all(k in params for k in ['nx', 'ny', 'nz', 'x', 'y', 'z']) or data_start_index == -1:
            print("エラー: PHITSファイルのメッシュパラメータが不完全、またはデータ開始行が見つかりません。", file=sys.stderr)
            return None

        data_lines = "".join(lines[data_start_index:])
        df_raw = pd.read_csv(StringIO(data_lines), sep=r'\s+', header=None, on_bad_lines='skip')
        
        dose_data = df_raw.iloc[:, -2].to_numpy(dtype=float)
        
        if len(dose_data) != params['nx'] * params['ny'] * params['nz']:
             print(f"エラー: データ点数({len(dose_data)})がメッシュ定義({params['nx'] * params['ny'] * params['nz']})と一致しません。", file=sys.stderr)
             return None

        dose_cube = dose_data.reshape(params['nz'], params['ny'], params['nx'])
        dose_cube = dose_cube.transpose(2, 1, 0)

        print(f"✅ PHITS 3Dメッシュデータを読み込みました (サイズ: {params['nx']}x{params['ny']}x{params['nz']})。")
        return {'x': params['x'], 'y': params['y'], 'z': params['z'], 'dose': dose_cube}

    except Exception as e:
        print(f"エラー: PHITSファイルの解析中に予期せぬ問題が発生しました - {e}", file=sys.stderr)
        return None

def extract_1d_profile(phits_data, axis, cx=0.0, cy=0.0, cz=0.0):
    """3Dデータから指定された軸と座標の1Dプロファイルを抽出する"""
    try:
        x_coords, y_coords, z_coords = phits_data['x'], phits_data['y'], phits_data['z']
        dose_cube = phits_data['dose']

        ix = np.argmin(np.abs(x_coords - cx))
        iy = np.argmin(np.abs(y_coords - cy))
        iz = np.argmin(np.abs(z_coords - cz))

        print(f"プロファイル抽出座標: X={x_coords[ix]:.3f}, Y={y_coords[iy]:.3f}, Z={z_coords[iz]:.3f} (cm) で断面を抽出。")

        if axis == 'x':
            pos, dose = x_coords, dose_cube[:, iy, iz]
        elif axis == 'y':
            pos, dose = y_coords, dose_cube[ix, :, iz]
        elif axis == 'z':
            pos, dose = z_coords, dose_cube[ix, iy, :]
        else:
            return None
        
        return pd.DataFrame({'pos': pos, 'dose': dose})

    except Exception as e:
        print(f"エラー: 1Dプロファイルの抽出中に問題が発生しました - {e}", file=sys.stderr)
        return None

def calculate_rmse(df_measured, df_phits):
    interp_measured_dose = np.interp(df_phits['pos'], df_measured['pos'], df_measured['dose_normalized'])
    return np.sqrt(np.mean((df_phits['dose_normalized'] - interp_measured_dose)**2))

def calculate_gamma_index(df_measured, df_phits, dose_ta, dist_ta_mm, dose_threshold):
    print(f"\n--- ガンマインデックス評価 (DTA={dist_ta_mm:.1f}mm, DD={dose_ta:.1f}%, Cutoff={dose_threshold:.1f}%) ---")
    axes_ref_mm = (df_measured['pos'].to_numpy() * 10,)
    dose_ref = df_measured['dose_normalized'].to_numpy()
    axes_eval_mm = (df_phits['pos'].to_numpy() * 10,)
    dose_eval = df_phits['dose_normalized'].to_numpy()
    gamma = pymedphys.gamma(axes_ref_mm, dose_ref, axes_eval_mm, dose_eval, dose_ta, dist_ta_mm, lower_percent_dose_cutoff=dose_threshold)
    valid_gamma = gamma[~np.isnan(gamma)]
    if len(valid_gamma) == 0:
        print("警告: 有効なガンマ値が一つも計算されませんでした。データ範囲やカットオフ値を確認してください。", file=sys.stderr)
        return 0.0
    return (np.sum(valid_gamma <= 1) / len(valid_gamma) * 100)

def save_results_to_text(report_dir, phits_file, measured_file, axis_params, analysis_params, rmse, gamma_pass_rate):
    base_phits = os.path.splitext(os.path.basename(phits_file))[0]
    base_measured = os.path.splitext(os.path.basename(measured_file))[0]
    report_filename = os.path.join(report_dir, f'Report_{base_phits}_vs_{base_measured}_axis-{axis_params["axis"]}.txt')
    content = f"""
    #--- 検証データ比較レポート ---#

    ## ファイル情報
    - PHITS出力ファイル名: {os.path.basename(phits_file)}
    - 実測データCSVファイル名: {os.path.basename(measured_file)}

    ## プロファイル抽出パラメータ
    - 抽出軸: {axis_params['axis']}
    - 断面座標: X={axis_params['cx']:.2f}, Y={axis_params['cy']:.2f}, Z={axis_params['cz']:.2f} (cm)

    ## 解析パラメータ
    - スケーリング係数: {analysis_params['scale']:.2f}
    - 平滑化 (Savitzky-Golay): window={analysis_params['window']}, order={analysis_params['order']}
    - ガンマ評価基準 (DD/DTA/Cutoff): {analysis_params['dd']:.1f}% / {analysis_params['dta']:.1f} mm / {analysis_params['cutoff']:.1f}%

    ## 解析結果
    - 平均二乗平方根誤差 (RMSE): {rmse:.4f}
    - ガンマインデックス パス率: {gamma_pass_rate:.2f} %
    """
    try:
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(dedent(content))
        print(f"✅ レポートを '{report_filename}' に保存しました。")
    except Exception as e:
        print(f"エラー: レポートファイルの保存中に問題が発生しました - {e}", file=sys.stderr)

def main():
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(script_dir)
    config_path = os.path.join(project_root, 'config.ini')

    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        print(f"エラー: 設定ファイル '{config_path}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
            
    config.read(config_path, encoding='utf-8')
    try:
        paths = config['Paths']
        phits_dir = os.path.join(project_root, paths.get('phits_data_dir', 'data/phits_output/'))
        measured_dir = os.path.join(project_root, paths.get('measured_data_dir', 'data/measured_csv/'))
        output_dir = os.path.join(project_root, paths.get('output_dir', 'output/'))
    except KeyError:
        print(f"エラー: '{config_path}' に '[Paths]' セクションがありません。", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description=f'PHITS 3Dメッシュデータから指定軸のプロファイルを抽出し、実測データと比較します。(Ver. {__version__})',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('phits_file', type=str, help='PHITS出力ファイル名 (3Dメッシュ)')
    parser.add_argument('measured_file', type=str, help='実測データCSVファイル名')
    parser.add_argument('--axis', type=str, required=True, choices=['x', 'y', 'z'], help='抽出するプロファイルの軸 (x, y, z)')
    parser.add_argument('--cx', type=float, default=0.0, help='プロファイル断面のX座標 (cm)')
    parser.add_argument('--cy', type=float, default=0.0, help='プロファイル断面のY座標 (cm)')
    parser.add_argument('--cz', type=float, default=0.0, help='プロファイル断面のZ座標 (cm)')
    parser.add_argument('--scale', type=float, default=1.0, help='PHITSデータへのスケーリング係数 (デフォルト: 1.0)')
    parser.add_argument('--window', type=int, default=5, help='平滑化のウィンドウ幅 (奇数, デフォルト: 5)')
    parser.add_argument('--order', type=int, default=2, help='平滑化の多項式次数 (デフォルト: 2)')
    parser.add_argument('--dd', type=float, default=3.0, help='ガンマ評価の線量差許容値(%%) (デフォルト: 3.0)')
    parser.add_argument('--dta', type=float, default=3.0, help='ガンマ評価の距離許容値(mm) (デフォルト: 3.0)')
    parser.add_argument('--cutoff', type=float, default=10.0, help='ガンマ評価の低線量カットオフ値(%%) (デフォルト: 10.0)')
    parser.add_argument('--no-plot', action='store_true', help='このフラグを立てるとグラフを画面に表示しません。')
    
    args = parser.parse_args()

    print(f"--- Comp_measured_phits.py Version: {__version__} ---")

    phits_filepath = os.path.join(phits_dir, args.phits_file)
    measured_filepath = os.path.join(measured_dir, args.measured_file)

    df_measured, measured_axis = load_measured_data(measured_filepath)
    phits_3d_data = parse_phits_3d_tally(phits_filepath)
    
    if phits_3d_data is None:
        print("\nエラー: PHITSデータ読み込みに失敗したため、処理を中断しました。", file=sys.stderr)
        sys.exit(1)

    df_phits_raw = extract_1d_profile(phits_3d_data, args.axis, args.cx, args.cy, args.cz)

    if df_measured is None or df_phits_raw is None:
        print("\nエラー: データ読み込みまたはプロファイル抽出に失敗したため、処理を中断しました。", file=sys.stderr)
        sys.exit(1)

    df_phits = df_phits_raw.copy()
    df_phits['dose_normalized'] = (df_phits['dose'] / df_phits['dose'].max()) * 100

    if args.scale != 1.0:
        df_phits['dose_normalized'] *= args.scale
        print(f"\n✅ 正規化後のPHITS線量データに係数 {args.scale} を適用しました。")

    if args.window % 2 == 0:
        print(f"エラー: 平滑化のウィンドウ幅は奇数である必要があります。指定値: {args.window}", file=sys.stderr)
        sys.exit(1)
    if args.window <= args.order:
        print(f"エラー: 多項式次数はウィンドウ幅より小さくする必要があります。指定値: window={args.window}, order={args.order}", file=sys.stderr)
        sys.exit(1)

    if len(df_phits) > args.window:
        df_phits['dose_smoothed'] = savgol_filter(df_phits['dose_normalized'], args.window, args.order)
        print(f"✅ Savitzky-Golayフィルターを適用しました (window={args.window}, order={args.order})。")
        df_phits_eval = df_phits.copy()
        df_phits_eval.rename(columns={'dose_smoothed': 'dose_final'}, inplace=True)
    else:
        print(f"警告: データ点数({len(df_phits)})がウィンドウ幅({args.window})以下です。平滑化をスキップしました。")
        df_phits_eval = df_phits.copy()
        df_phits_eval.rename(columns={'dose_normalized': 'dose_final'}, inplace=True)

    rmse_value = calculate_rmse(df_measured, df_phits_eval.rename(columns={'dose_final': 'dose_normalized'}))
    print(f"\n✅ 平均二乗平方根誤差 (RMSE): {rmse_value:.4f}")
    
    gamma_pass_rate = calculate_gamma_index(df_measured, df_phits_eval.rename(columns={'dose_final': 'dose_normalized'}), args.dd, args.dta, args.cutoff)
    print(f"✅ ガンマインデックス パス率: {gamma_pass_rate:.2f} %")
    
    plt.figure(figsize=(12, 8))
    plt.scatter(df_measured['pos'], df_measured['dose_normalized'], label=f'Measured ({args.measured_file})', color='blue', s=20, alpha=0.7, zorder=5)
    plt.plot(df_phits['pos'], df_phits['dose_normalized'], label=f'PHITS (Original Extracted)', color='gray', linestyle=':', lw=2, alpha=0.8)
    plt.plot(df_phits_eval['pos'], df_phits_eval['dose_final'], label=f'PHITS (Scaled & Smoothed)', color='red', lw=2.5)
    
    plt.title(f'Comparison: PHITS vs. Measured ({args.axis}-axis profile)', fontsize=16)
    plt.xlabel(f'Position ({args.axis}-axis, cm)', fontsize=12)
    plt.ylabel('Normalized Dose (%)', fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--')
    plt.ylim(0, 110)
    
    plot_dir = os.path.join(output_dir, "plots")
    report_dir = os.path.join(output_dir, "reports")
    os.makedirs(plot_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
        
    output_filename = os.path.join(plot_dir, f'Comp_{os.path.splitext(args.phits_file)[0]}_vs_{os.path.splitext(args.measured_file)[0]}_axis-{args.axis}.png')
    plt.savefig(output_filename)
    print(f"\n✅ グラフを '{output_filename}' に保存しました。")

    axis_params = {'axis': args.axis, 'cx': args.cx, 'cy': args.cy, 'cz': args.cz}
    analysis_params = {'scale': args.scale, 'window': args.window, 'order': args.order, 'dd': args.dd, 'dta': args.dta, 'cutoff': args.cutoff}

    save_results_to_text(report_dir, args.phits_file, args.measured_file, axis_params, analysis_params, rmse_value, gamma_pass_rate)
    
    if not args.no_plot:
        plt.show()

if __name__ == '__main__':
    main()