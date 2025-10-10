# **Comp\_measured\_phits\_v9.py (完全版)**
# Comp_measured_phits_v9.py
import pandas as pd
import numpy as np
import math
import os
import sys
from io import StringIO
import re
from textwrap import dedent
import argparse
import configparser # INIファイル読み込みのために追加

# --- 依存ライブラリのチェック ---
try:
    import matplotlib.pyplot as plt
    import pymedphys
    from scipy.signal import savgol_filter
except ModuleNotFoundError as e:
    print(f"エラー: 必要なライブラリがインストールされていません - {e}", file=sys.stderr)
    print("次のコマンドでインストールしてください: pip install pandas numpy matplotlib pymedphys scipy", file=sys.stderr)
    sys.exit(1)

__version__ = "9.0.CONFIG_INI"

# --- 対話モード用の関数 (INI設定を反映) ---
def select_file_from_menu(directory, extensions, description):
    """指定されたディレクトリから対話形式でファイルを選択する"""
    if not os.path.isdir(directory):
        print(f"エラー: 設定ファイル(config.ini)に指定されたディレクトリが見つかりません: {directory}", file=sys.stderr)
        return None
        
    files = [f for f in os.listdir(directory) if any(f.endswith(ext) for ext in extensions)]
    if not files:
        print(f"エラー: '{directory}'内に {description} ({', '.join(extensions)}) が見つかりません。", file=sys.stderr)
        return None
        
    print(f"\n--- {description}を選択してください ---")
    for i, f in enumerate(files):
        print(f"  [{i+1}] {f}")
    while True:
        try:
            choice = int(input("ファイルの番号を入力してください: "))
            if 1 <= choice <= len(files):
                selected_file = files[choice - 1]
                print(f"  >> '{selected_file}' を選択しました。")
                return selected_file
            else:
                print("エラー: リストにない番号です。再入力してください。")
        except ValueError:
            print("エラー: 番号を整数で入力してください。")

# --- データ読み込み・解析関数 ---

def load_measured_data(file_path):
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

def parse_phits_profile(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        last_tally_start_index = next((i for i in range(len(lines) - 1, -1, -1) if '[t-deposit]' in lines[i].replace(' ', '').lower()), -1)
        if last_tally_start_index == -1: return None, None
        nx, ny, nz = 1, 1, 1
        for line in lines[last_tally_start_index:]:
            sline = line.strip()
            if sline.startswith('nx ='): nx = int(sline.split('=')[1].split('#')[0].strip())
            elif sline.startswith('ny ='): ny = int(sline.split('=')[1].split('#')[0].strip())
            elif sline.startswith('nz ='): nz = int(sline.split('=')[1].split('#')[0].strip())
            elif sline.startswith('#') and ('total' in sline or 'all' in sline): break
        profile_axis = None
        if ny > 1 and nx == 1 and nz == 1: profile_axis = 'y'
        elif nx > 1 and ny == 1 and nz == 1: profile_axis = 'x'
        elif nz > 1 and nx == 1 and ny == 1: profile_axis = 'z'
        else: return None, None
        header_line_index, data_start_index = -1, -1
        header_columns = []
        for i in range(last_tally_start_index, len(lines) - 1):
            line1 = lines[i].strip()
            if line1.startswith('#'):
                header_words = line1.replace('#', '').strip().split()
                is_axis_present = profile_axis in header_words or f'{profile_axis}-lower' in header_words
                is_dose_present = 'total' in header_words or 'all' in header_words
                if is_axis_present and is_dose_present:
                    for j in range(i + 1, len(lines)):
                        data_line_candidate = lines[j].strip()
                        if data_line_candidate and not data_line_candidate.startswith('#'):
                            header_line_index = i
                            data_start_index = j
                            header_columns = header_words
                            break
                    if header_line_index != -1:
                        break
        if header_line_index == -1: return None, None
        num_columns = len(header_columns)
        data_lines = []
        for line in lines[data_start_index:]:
            parts = line.strip().split()
            if len(parts) != num_columns: break
            data_lines.append(line)
        if not data_lines: return None, None
        temp_df = pd.read_csv(StringIO("".join(data_lines)), sep=r'\s+', header=None, names=header_columns, engine='python')
        temp_df.dropna(inplace=True)
        df = pd.DataFrame()
        if profile_axis in temp_df.columns: df['pos_center'] = temp_df[profile_axis]
        elif f'{profile_axis}-lower' in temp_df.columns: df['pos_center'] = (temp_df[f'{profile_axis}-lower'] + temp_df[f'{profile_axis}-upper']) / 2
        else: df['pos_center'] = temp_df.iloc[:, 0]
        dose_col = 'total' if 'total' in temp_df.columns else 'all'
        df['dose'] = temp_df[dose_col]
        print(f"✅ PHITS(生)データを正常に読み込みました。(プロファイル軸: {profile_axis})")
        return df, profile_axis
    except FileNotFoundError:
        print(f"エラー: PHITSファイルが見つかりません: {file_path}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"エラー: PHITSファイルの解析中に予期せぬ問題が発生しました - {e}", file=sys.stderr)
        return None, None

def calculate_rmse(df_measured, df_phits):
    interp_measured_dose = np.interp(df_phits['pos_center'], df_measured['pos'], df_measured['dose_normalized'])
    return np.sqrt(np.mean((df_phits['dose_normalized'] - interp_measured_dose)**2))

def calculate_gamma_index(df_measured, df_phits, dose_ta, dist_ta_mm, dose_threshold):
    print(f"\n--- ガンマインデックス評価 (DTA={dist_ta_mm:.1f}mm, DD={dose_ta:.1f}%, Cutoff={dose_threshold:.1f}%) ---")
    axes_ref_mm = (df_measured['pos'].to_numpy() * 10,)
    dose_ref = df_measured['dose_normalized'].to_numpy()
    axes_eval_mm = (df_phits['pos_center'].to_numpy() * 10,)
    dose_eval = df_phits['dose_normalized'].to_numpy()
    gamma = pymedphys.gamma(
        axes_ref_mm, dose_ref, axes_eval_mm, dose_eval, dose_ta, dist_ta_mm,
        lower_percent_dose_cutoff=dose_threshold)
    valid_gamma = gamma[~np.isnan(gamma)]
    if len(valid_gamma) == 0:
        print("警告: 有効なガンマ値が一つも計算されませんでした。データ範囲やカットオフ値を確認してください。", file=sys.stderr)
        return 0.0
    return (np.sum(valid_gamma <= 1) / len(valid_gamma) * 100)

def save_results_to_text(report_dir, phits_file, measured_file, scaling_factor, 
                         smoothing_params, gamma_criteria, rmse, gamma_pass_rate):
    base_phits = os.path.splitext(os.path.basename(phits_file))[0]
    base_measured = os.path.splitext(os.path.basename(measured_file))[0]
    report_filename = os.path.join(report_dir, f'Report_{base_phits}_vs_{base_measured}.txt')
    content = f"""
    #--- 検証データ比較レポート ---#

    ## ファイル情報
    - PHITS出力ファイル名: {os.path.basename(phits_file)}
    - 実測データCSVファイル名: {os.path.basename(measured_file)}

    ## 解析パラメータ
    - スケーリング係数: {scaling_factor:.2f}
    - 平滑化 (Savitzky-Golay): window={smoothing_params['window']}, order={smoothing_params['order']}
    - ガンマ評価基準 (DD/DTA/Cutoff): {gamma_criteria['dose_ta']:.1f}% / {gamma_criteria['dist_ta_mm']:.1f} mm / {gamma_criteria['cutoff']:.1f}%

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


# Comp_measured_phits_v9.1.py
import pandas as pd
import numpy as np
import math
import os
import sys
from io import StringIO
import re
from textwrap import dedent
import argparse
import configparser

# (依存ライブラリのチェックは同じ)

__version__ = "9.1.ROBUST_PATH"

# (select_file_from_menu, load_measured_data, parse_phits_profile, 
#  calculate_rmse, calculate_gamma_index, save_results_to_text の各関数はv9と同じ)
# ...

# --- メイン処理 ---
def main():
    # --- パスの設定をより頑健に ---
    # スクリプト自身の絶対パスを取得
    script_path = os.path.abspath(__file__)
    # スクリプトが置かれているディレクトリを取得 (e.g., .../src)
    script_dir = os.path.dirname(script_path)
    # プロジェクトのルートディレクトリを取得 (e.g., .../phits-linac-validation)
    project_root = os.path.dirname(script_dir)

    # config.iniはプロジェクトルートにあると仮定
    config_path = os.path.join(project_root, 'config.ini')

    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        print(f"エラー: 設定ファイル '{config_path}' が見つかりません。", file=sys.stderr)
        print("プロジェクトのルートディレクトリに 'config.ini' を配置してください。")
        sys.exit(1)
            
    config.read(config_path, encoding='utf-8')
    try:
        paths = config['Paths']
        # パスをプロジェクトルートからの相対パスとして解釈
        phits_dir = os.path.join(project_root, paths.get('phits_data_dir', 'data/phits_output/'))
        measured_dir = os.path.join(project_root, paths.get('measured_data_dir', 'data/measured_csv/'))
        output_dir = os.path.join(project_root, paths.get('output_dir', 'output/'))
    except KeyError:
        print(f"エラー: '{config_path}' に '[Paths]' セクションがありません。", file=sys.stderr)
        sys.exit(1)
        
    parser = argparse.ArgumentParser(
        description=f'PHITSシミュレーション結果と実測データを比較・評価します。(Ver. {__version__})\n引数を指定しない場合は対話モードで起動します。',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('phits_file', nargs='?', default=None, type=str, help=f'PHITS出力ファイル名 ({phits_dir}内)')
    parser.add_argument('measured_file', nargs='?', default=None, type=str, help=f'実測データCSVファイル名 ({measured_dir}内)')
    parser.add_argument('--scale', type=float, default=1.0, help='PHITSデータへのスケーリング係数 (デフォルト: 1.0)')
    parser.add_argument('--window', type=int, default=5, help='平滑化のウィンドウ幅 (奇数, デフォルト: 5)')
    parser.add_argument('--order', type=int, default=2, help='平滑化の多項式次数 (デフォルト: 2)')
    parser.add_argument('--dd', type=float, default=3.0, help='ガンマ評価の線量差許容値(%%) (デフォルト: 3.0)')
    parser.add_argument('--dta', type=float, default=3.0, help='ガンマ評価の距離許容値(mm) (デフォルト: 3.0)')
    parser.add_argument('--cutoff', type=float, default=10.0, help='ガンマ評価の低線量カットオフ値(%%) (デフォルト: 10.0)')
    parser.add_argument('--no-plot', action='store_true', help='このフラグを立てるとグラフを画面に表示しません。')
    
    args = parser.parse_args()

    print(f"--- Comp_measured_phits.py Version: {__version__} ---")

    # --- モード分岐 ---
    if args.phits_file and args.measured_file:
        print("▶ コマンドライン引数モードで実行します。")
        phits_file = args.phits_file
        measured_file = args.measured_file
        scaling_factor = args.scale
        window_length = args.window
        polyorder = args.order
        dose_ta = args.dd
        dist_ta_mm = args.dta
        cutoff = args.cutoff
        show_plot = not args.no_plot
    else:
        print("▶ 対話モードで実行します。")
        phits_file = select_file_from_menu(phits_dir, ['.out', '.dat'], "PHITS出力ファイル")
        if not phits_file: sys.exit(1)
        measured_file = select_file_from_menu(measured_dir, ['.csv'], "実測データCSVファイル")
        if not measured_file: sys.exit(1)
        
        try:
            print("\n--- 解析パラメータを入力してください (空欄でEnterを押すとデフォルト値が使われます) ---")
            scaling_factor = float(input("スケーリング係数 [デフォルト: 1.0]: ") or "1.0")
            window_length = int(input("平滑化ウィンドウ幅 (奇数) [デフォルト: 5]: ") or "5")
            polyorder = int(input("平滑化多項式次数 [デフォルト: 2]: ") or "2")
            dose_ta = float(input("ガンマ線量差許容値 (%) [デフォルト: 3.0]: ") or "3.0")
            dist_ta_mm = float(input("ガンマ距離許容値 (mm) [デフォルト: 3.0]: ") or "3.0")
            cutoff = float(input("ガンマ低線量カットオフ値 (%) [デフォルト: 10.0]: ") or "10.0")
            show_plot = True
        except ValueError:
            print("エラー: 数値の入力が不正です。処理を中断します。", file=sys.stderr)
            sys.exit(1)

    # --- ファイルパスの結合 ---
    phits_filepath = os.path.join(phits_dir, phits_file)
    measured_filepath = os.path.join(measured_dir, measured_file)
    
    # --- 共通の解析処理 ---
    df_measured, measured_axis = load_measured_data(measured_filepath)
    df_phits_raw, phits_axis = parse_phits_profile(phits_filepath)
    if df_measured is None or df_phits_raw is None:
        print("\nエラー: データ読み込みに失敗したため、処理を中断しました。", file=sys.stderr)
        sys.exit(1)

    if phits_axis and measured_axis:
        is_match = (phits_axis == measured_axis) or \
                   (phits_axis == 'z' and measured_axis == 'y') or \
                   (phits_axis == 'y' and measured_axis == 'z')
        if not is_match:
            print(f"\n警告: PHITS軸({phits_axis})と測定軸({measured_axis})の対応が不正の可能性があります。")
        else:
            print(f"✅ 座標系は正しく対応しています (PHITS: {phits_axis}, 測定: {measured_axis})。")

    df_phits = df_phits_raw.copy()
    df_phits['dose_normalized'] = (df_phits['dose'] / df_phits['dose'].max()) * 100

    if scaling_factor != 1.0:
        df_phits['dose_normalized'] *= scaling_factor
        print(f"\n✅ 正規化後のPHITS線量データに係数 {scaling_factor} を適用しました。")

    if window_length % 2 == 0:
        print(f"エラー: 平滑化のウィンドウ幅は奇数である必要があります。指定値: {window_length}", file=sys.stderr)
        sys.exit(1)
    if window_length <= polyorder:
        print(f"エラー: 多項式次数はウィンドウ幅より小さくする必要があります。指定値: window={window_length}, order={polyorder}", file=sys.stderr)
        sys.exit(1)

    if len(df_phits) > window_length:
        df_phits['dose_smoothed'] = savgol_filter(df_phits['dose_normalized'], window_length, polyorder)
        print(f"✅ Savitzky-Golayフィルターを適用しました (window={window_length}, order={polyorder})。")
        df_phits_eval = df_phits.copy()
        df_phits_eval['dose_normalized'] = df_phits['dose_smoothed']
    else:
        print(f"警告: データ点数({len(df_phits)})がウィンドウ幅({window_length})以下です。平滑化をスキップしました。")
        df_phits_eval = df_phits
        df_phits['dose_smoothed'] = df_phits['dose_normalized']

    rmse_value = calculate_rmse(df_measured, df_phits_eval)
    print(f"\n✅ 平均二乗平方根誤差 (RMSE): {rmse_value:.4f}")
    
    gamma_pass_rate = calculate_gamma_index(df_measured, df_phits_eval, 
                                            dose_ta=dose_ta, 
                                            dist_ta_mm=dist_ta_mm, 
                                            dose_threshold=cutoff)
    print(f"✅ ガンマインデックス パス率: {gamma_pass_rate:.2f} %")
    
    plt.figure(figsize=(12, 8))
    plt.scatter(df_measured['pos'], df_measured['dose_normalized'], label=f'Measured ({measured_file})', color='blue', s=20, alpha=0.7, zorder=5)
    original_normalized = (df_phits_raw.copy()['dose'] / df_phits_raw.copy()['dose'].max()) * 100
    plt.plot(df_phits['pos_center'], original_normalized, label=f'PHITS ({phits_file}, Original Norm.)', color='gray', linestyle=':', lw=2, alpha=0.8)
    plt.plot(df_phits['pos_center'], df_phits['dose_smoothed'], label=f'PHITS ({phits_file}, Scaled & Smoothed)', color='red', lw=2.5)
    
    plt.title('Comparison: PHITS Simulation vs. Measured Profile', fontsize=16)
    plt.xlabel('Position (cm)', fontsize=12)
    plt.ylabel('Normalized Dose (%)', fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--')
    try:
        x_min = min(df_measured['pos'].min(), df_phits['pos_center'].min())
        x_max = max(df_measured['pos'].max(), df_phits['pos_center'].max())
        plt.xlim(x_min - 1, x_max + 1)
    except:
        plt.xlim(-15, 15)
    plt.ylim(0, 110)
    
    # --- 結果の保存 ---
    plot_dir = os.path.join(output_dir, "plots")
    report_dir = os.path.join(output_dir, "reports")
    os.makedirs(plot_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
        
    output_filename = os.path.join(plot_dir, f'Comp_{os.path.splitext(phits_file)[0]}_vs_{os.path.splitext(measured_file)[0]}.png')
    plt.savefig(output_filename)
    print(f"\n✅ グラフを '{output_filename}' に保存しました。")

    smoothing_params = {'window': window_length, 'order': polyorder}
    gamma_criteria = {'dose_ta': dose_ta, 'dist_ta_mm': dist_ta_mm, 'cutoff': cutoff}

    save_results_to_text(
        report_dir,
        phits_file,
        measured_file,
        scaling_factor,
        smoothing_params,
        gamma_criteria,
        rmse_value,
        gamma_pass_rate
    )
    
    if show_plot:
        plt.show()

if __name__ == '__main__':
    main()