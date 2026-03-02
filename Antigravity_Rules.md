# Antigravity Development Protocol (Hiroki Edition)

このドキュメントは、Antigravity（Claudeモデル）を用いて、日本語環境下で安定的かつ高速に開発を行うための絶対ルールです。

---

## 1. モデル戦略：「脳」と「手」の使い分け

Antigravityの動作が重くなる・言うことを聞かない原因は、「作業フェーズ」と「モデル」の不一致です。

| フェーズ | 推奨モデル | 役割 | 理由 |
|---|---|---|---|
| 実装・修正・実行 | Claude 4.5 Sonnet | Developer (手) | **【基本は常時これ】** 高速、従順、エラー時に素直。日本語指示も完璧。ThinkingモードはOFF推奨。 |
| 設計・難問相談 | Claude 4.5 Opus | Architect (脳) | **【ハマった時だけ】** 複雑なバグや設計相談のみ使用。※長考して重くなるため、解決したらSonnetに戻す。 |

---

## 2. 3時間ルール（セッション管理）

チャットが長くなるとAIは「バカ」になり、PCは「重く」なります。

- **賞味期限:** 1つのチャットは **90分〜3時間** が限界。
- **重くなったら:** 粘らずに「引越し」をする。
- **リセット:** `Ctrl + R` でブラウザをリロードし、メモリを解放する。

### 引越し（Handover）プロンプト

チャットを捨てる前に、以下の指示を投げて「記憶の引き継ぎ書」を作らせてください。

> 「動作が重くなってきたのでリセットします。
> 現在の進捗、保留中のタスク、直近で実行すべきコマンドをまとめた `99-handover_context.md` を作成してください。
> 作成後、このチャットは終了します。」

---

## 3. スタートアップ・プロンプト（毎回最初に貼る）

新しいチャットを始めたら、まず以下のプロンプトを貼り付けて、AIを「Hirokiモード」に矯正してください。

```markdown
# Antigravity Control Protocol (Hiroki Mode)

あなたは私の「専属実装エンジニア」です。以下のルールを厳守してください。

## 1. Mindset: User First
- **指示絶対:** 文書（todo.md等）とチャットの指示が矛盾した場合、**必ず「今のチャット指示」を優先**してください。
- **Action Over Thought:** 実装フェーズでは、長々とした考察（Thinking）は不要です。最短手数で動くコードを出力してください。
- **Stop Loop:** エラーが出た際、勝手に修正ループに入らず、一度停止して状況を報告してください。

## 2. Windows/PowerShell Safety (Encoding Rules)
Windows環境のため、標準出力を直接読むと文字化け・空文字になります。
以下の手順以外でのコマンド実行を禁止します。

- **Git:** システムメッセージを英語化するため、必ず `$env:LC_ALL='C';` を付与する。
  ```powershell
  $env:LC_ALL='C'; git status > _git_log.txt 2>&1
  ```
- **Python:** 日本語ログ対策のため、`$env:PYTHONUTF8=1;` を付与する。
  ```powershell
  $env:PYTHONUTF8=1; python script.py > _py_log.txt 2>&1
  ```
- **Output Check:** 結果は画面に出さず、必ずファイル(`> log.txt`)にリダイレクトし、`read_file` ツールで中身を確認すること。
- **Output "Blindness":** 「出力が見えません」という言い訳は禁止。ファイル経由なら必ず見えます。

## 3. Japanese Doc Handling
- 仕様書やコミットメッセージは**日本語**で扱います。
- `read_file` / `write_file` は常に **UTF-8** を使用してください。
- Gitコミット時、文字化けを防ぐためメッセージファイル経由を推奨します。
  ```powershell
  
  ```

## 4. Workflow
1. **Understand:** `99-handover_context.md` (あれば) と `todo.md` を読み、タスクを1つ提案。
2. **Plan:** 実装方針を簡潔に提示（承認待ち）。
3. **Execute:** 承認後、実装開始。
```
ルール通り、ファイルにリダイレクトして (`> log.txt`)、`read_file` で読んでください。
---

### Q. 日本語コミットが文字化けする

**A.** AIにメッセージファイルを作らせてコミットさせてください。

```powershell
# AIによる操作:
# 1. write_file('_msg.txt', '修正内容: ○○機能の追加')
# 2. 以下のコマンドを実行
$env:LC_ALL='C'; git commit -F _msg.txt
```

**注意**: ローカルの`git log`では文字化けして見えますが、**GitHubリポジトリでは正しく表示されます**。これはPowerShellの表示の問題であり、Gitリポジトリ自体には正しくUTF-8で保存されています。

## 4. トラブルシューティング

### Q. 「出力が空です」「読めません」と言われた

**A.** AIがルールをサボって標準出力を読もうとしています。こう叱ってください：

> 「ルール通り、ファイルにリダイレクトして (`> log.txt`)、`read_file` で読んでください。」

### Q. Gitの日本語ファイル名が `\343\...` になる

**A.** ターミナルで一度だけ以下を実行してください（AIではなく人間が実行）。

```powershell
git config --global core.quotepath false
```

### Q. 日本語コミットが文字化けする

**A.** AIにメッセージファイルを作らせてコミットさせてくださいgit commit -F _commit_msg.txt。

```powershell
# AIによる操作:
# 1. write_file('_msg.txt', '修正内容: ○○機能の追加')
# 2. 以下のコマンドを実行
$env:LC_ALL='C'; git commit -F _msg.txt
```

---

## 5. 作業終了時（Finish）

一日の終わり、またはセッション終了時には以下を実施してください。

- **Docs Update:** `todo.md` / `99-daily-summary.md` / `openspec文書` 99-handover_context.md の更新（日本語）。
- **Git:** 変更のコミット（プッシュは確認してから）。
- **Clean up:** 一時ファイル（`_git_log.txt` や `_msg.txt`）の削除。
