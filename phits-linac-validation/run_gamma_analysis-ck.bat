@echo off
rem --- この下の行のパスを自分の環境に合わせて書き換えてください ---
cd /d "C:\Users\放射治療研究用PC\Documents\Python\phits-linac-validation"

echo --- PHITS線量分布評価を実行します ---
echo --- 深度1.5cmの比較 Z軸プロファイルの比較 ---
python src/Comp_measured_phits_v9.1.py deposit-y-water-15.out I150-1.5.csv --scale 1.00 --window 5 --order 2 --dd 2.0 --dta 2.0 --cutoff 10.0 --no-plot
echo --- 深度5cmの比較 Z軸プロファイルの比較 ---
python src/Comp_measured_phits_v9.1.py deposit-y-water-50.out I150-5.0.csv --scale 1.00 --window 5 --order 2 --dd 2.0 --dta 2.0 --cutoff 10.0 --no-plot
echo --- 深度10cmの比較 Z軸プロファイルの比較 ---
python src/Comp_measured_phits_v9.1.py deposit-y-water-100.out I150-10.0.csv --scale 1.00 --window 5 --order 2 --dd 2.0 --dta 2.0 --cutoff 10.0 --no-plot
echo --- 深度20cmの比較 Z軸プロファイルの比較 ---
python src/Comp_measured_phits_v9.1.py deposit-y-water-200.out I150-20.0.csv --scale 1.00 --window 5 --order 2 --dd 2.0 --dta 2.0 --cutoff 10.0 --no-plot
echo --- 深度30cmの比較 Z軸プロファイルの比較 ---
python src/Comp_measured_phits_v9.1.py deposit-y-water-300.out I150-30.0.csv --scale 1.00 --window 5 --order 2 --dd 2.0 --dta 2.0 --cutoff 10.0 --no-plot
echo --- 深部線量分布(PDD)の比較 ---
python src/Comp_measured_phits_v9.1.py deposit-z-water.out I600-PDD.csv --scale 1.00 --window 11 --order 7 --dd 2.0 --dta 2.0 --cutoff 10.0 --no-plot
echo --- 処理が完了しました ---
pause