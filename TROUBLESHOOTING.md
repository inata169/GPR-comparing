# Troubleshooting

## Common Issues
- FileNotFoundError on report paths
  - Cause: parent directory missing.
  - Fix: tool now auto-creates directories when dirname is non-empty. Pass full paths like `phits-linac-validation/output/rtgamma/run3d`.
- Missing TransferSyntaxUID in DICOM
  - Cause: non-Part 10 files or incomplete meta.
  - Fix: loader defaults to ImplicitVRLittleEndian when absent.
- Very low pass rates for different systems
  - Cause: true geometric/scale differences across sources (grid size, scaling, origin).
  - Action: confirm with 2D visuals and logs; try `--dd 3 --dta 3` or ROI-limited evaluation.
- Multi-line commands on PowerShell fail
  - Use single-line `python -m ...` or separate lines; avoid here-docs.
- PowerShell string with colon and variables fails (InvalidVariableReference)
  - Use composite formatting: `"x:{0}:{0}:1" -f $dx` instead of `"x:$dx:$dx:1"`.
- Matplotlib display issues on servers
  - Use non-interactive save only (default) or set `MPLBACKEND=Agg`.
- Line endings / CRLF warnings in Git
  - Prefer text files with LF; avoid committing generated binaries/outputs.

## CI: Ruff import-sort error (I001)

**症状**: GitHub Actions が `ruff check` ステップで `I001 Import block is un-sorted or un-formatted` を報告してCIが落ちる。

**原因**: サードパーティ製ライブラリのインポートブロック内に余分な空行が含まれるとRuffがこれを不正とみなす。
例えば `try-except` ラッパーを除去したときに空行が残りやすい：
```python
# NG
import numpy as np

import pydicom
```
```python
# OK
import numpy as np
import pydicom
```

**対策**:
1. ローカルで先に `ruff check rtgamma/ tests/ scripts/ --fix` を実行してから commit する。
2. CI が `I001` で落ちた場合は `ruff check --fix` を実行し、変更をコミットして push すれば解消する。

## Windows: git push の認証失敗（トークン再発行後）

**症状**: GitHub の Personal Access Token を再発行した後、`git push` が失敗（または `Everything up-to-date` と表示されるが実際にはpushされていない）。PowerShellのリダイレクト（`>`）のログがUTF-16LEで書き込まれるため読めず、エラーに気づけない。

**原因**:
- PAT を再発行するとローカルの認証情報キャッシュが古くなり、push が 403/401 で弾かれる。
- PowerShell のリダイレクト（`> log.txt`）がデフォルトでUTF-16LEで書くため、`read_file`（UTF-8想定）で文字化けし、エラーメッセージが確認できない。

**対策**:
1. PAT 再発行後は Windows の資格情報マネージャー（`コントロール パネル > 資格情報マネージャー > Windows 資格情報`）から `github.com` の古いエントリを削除し、次回 push 時に新しいトークンを入力する。
2. git コマンドの出力確認は PowerShell リダイレクトではなく、**Python スクリプト経由**（`subprocess.run` + `open(log, 'w', encoding='utf-8')`）で UTF-8 ログファイルに書き出す。

## Performance Tips
- Use `--opt-shift on` with coarse-to-fine (default) for balanced runtime.
- Keep search ranges tight for clinical QA (e.g., `x:-3:3:1,y:-3:3:1,z:-3:3:1`).
- Numba JIT: first call may be slower; subsequent runs are faster.
- Wide search is expensive: prefer two-stage search
  - Coarse: e.g., `x:-150:150:10,y:-30:30:10,z:-30:30:10, --refine none`
  - Refine around the best: e.g., `x:75:85:1,y:-55:-45:1,z:-25:-15:1, --refine coarse2fine`

## Validation Checklist
- Self-compare of a single RTDOSE yields ~100% pass.
- Pair logs show IPP/IOP/PixelSpacing/GFOV echoed; verify expected geometry.
- Outputs saved under `phits-linac-validation/output/rtgamma/` with CSV/JSON/MD and images for 2D.
- Check report fields for geometry sanity:
  - `same_for_uid==true`, `orientation_min_dot≈1.0`, small `best_shift_mag_mm` in absolute runs.
