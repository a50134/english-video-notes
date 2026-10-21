---
name: english-video-notes
description: 貼上英文影片網址（YouTube 等），自動下載音檔和字幕、逐句對時剪出原音、寫中文翻譯與文法筆記，排成 N 天跟讀計畫建到 Notion（每句附原音）。當使用者說 /english-video-notes、貼影片網址並說「做成 Notion 筆記」「做成跟讀筆記」「匯入這部影片」「幫我做這部的 shadowing 筆記」時使用。也可用本機的影片／音檔加字幕檔。
---

# english-video-notes：影片網址 → Notion 跟讀筆記

輸入：影片網址（或本機影音檔）＋天數（沒說就問，預設 10 天）。
輸出：Notion 上一個總覽頁＋每天一頁（流程打勾清單、逐句英文／中文／原音／文法／例句／我的造句／🔴 不熟），最後一天是總複習。

腳本在本 skill 的 `scripts/`，一律用 `py -3.13` 執行（套件裝在這個版本）。全程用繁體中文回報。

## 規則
- 影音是有版權的內容，只供使用者個人學習：音檔只留在本機和使用者自己的 Notion，**不要**放到 GitHub 或任何公開位置。
- 不要自己安裝東西。`check.py` 顯示缺套件或缺模型時，先問使用者同意再裝。
- Notion 上使用者編輯過的頁面，不要用 `replace_content` 整頁覆寫；只用 `update_content` 改指定區塊。
- 不要開子代理（除非使用者要求）；筆記分批自己寫。

## 0. 預檢
```
py -3.13 scripts/check.py
py -3.13 scripts/fetch.py "<網址>" "<工作資料夾>" --check
```
工作資料夾用 `C:\Users\a5013\Desktop\Codex-project\video-notes\<影片短名>`（英數加連字號）。
`--check` 只查資料不下載，會顯示片名、長度、有沒有人工英文字幕／中文字幕。把這些和預估句數（大約每分鐘 15–20 句）告訴使用者，確認天數後再往下。超過 40 分鐘的影片先提醒筆記量很大，建議分段或拉長天數。

## 1. 下載音檔和字幕
```
py -3.13 scripts/fetch.py "<網址>" "<工作資料夾>"
```
本機檔案：`fetch.py "<影音檔>" "<工作資料夾>" --subs "<英文.srt>" [--zh-subs "<中文.srt>"]`
產生 `audio.mp3`、`en.vtt`／`zh.vtt`（有的話）、`meta.json`。
- YouTube 回「This video is not available」：fetch.py 會自動改用 android 等其他用戶端重試，並用 Node.js 當 JavaScript 執行環境；還是失敗就請使用者同意後更新 yt-dlp。
- 字幕用 Python 自己下載（yt-dlp 的 curl 在這台電腦會出現憑證錯誤）。YouTube 的自動字幕沒有標點又會重複，所以不用；沒有人工字幕時，文字改用語音辨識的結果。

## 2. 斷句＋對時
```
py -3.13 scripts/segment.py "<工作資料夾>"
```
語音辨識約花音檔長度的四分之一時間，超過 2 分鐘就用背景執行。產生 `sentences.json`，每句有 `en`、起訖秒數 `s`/`e`、`conf`（1＝每個字都在聲音裡找到）、`heard`（辨識到的文字）、`zhSub`（中文字幕，僅供參考）、`skip`。

接著**人工檢查並直接改 `sentences.json`**：
- `skip` 改成 `true`：整句只有人名、字幕製作資訊（Captioning by…）、純音效。重複句和尖叫聲已自動標成 skip。
- 修 `en`：字幕全大寫時改回正常大小寫（參考 `heard`）；語音辨識的文字要校對人名和專有名詞。
- 太長的句子（歌詞、沒有標點的連續句）拆成多筆，各自填 `s`/`e`（用 `words.json` 裡每個字的時間）；太碎的可以合併。
- `conf` 低於 0.6 的列出來，之後請使用者聽一下原音是否對得上（語音辨識抓不到的句子會改用字幕本身的時間）。
- 同一行字幕裡有好幾句、時間一樣的，合併成一句，否則會剪出一樣的音檔。
- 系列作的主題曲如果之前的集數已學過，可以整段排除。
- 大量修改用一個 Python 檔（SKIP 清單、TEXT 改字、TIME 改時間、MERGE 合併）一次套用，方便重跑。

## 3. 分配天數＋剪音檔
```
py -3.13 scripts/plan.py "<工作資料夾>" --days <N>
```
前 N−1 天平均分配句子，第 N 天總複習。產生 `plan.json` 和 `clips\Day<D>-<NN>.mp3`。把 `plan.json` 的 `title` 改成簡短片名。
某句原音開頭或結尾被切掉：改 `plan.json` 裡那句的 `s`/`e`，再跑 `plan.py "<工作資料夾>" --days <N> --only Day3-07`。

## 4. 寫筆記
每天一個檔 `notes\day<D>.json`，用 Write 工具寫（不要用 heredoc，中文會亂碼）：
```json
{"Day1-01": {"zh": "自然的繁體中文翻譯",
             "grammar": ["**句型或片語**：說明", "…"],
             "usage": "（可省略）什麼情境會這樣說",
             "example": "A new everyday sentence using the same pattern.",
             "exampleZh": "例句的中文"}}
```
- `grammar` 每句 2–5 點，挑這句真正值得學的句型、片語、口語用法；B1 程度看得懂的說明。
- 例句要是生活會用到的新句子，不要只換一個字。
- `py -3.13 scripts/render.py "<工作資料夾>" todo` 查還缺哪些。

## 5. 上傳原音到 Notion
每個音檔：
1. 呼叫 Notion 連接器的 `notion-create-file-upload`（`filename` = `Day1-01.mp3`），拿到 `upload_url`、授權標頭和 file upload id。
2. `bash scripts/upload.sh "<工作資料夾>" Day1-01 "<upload_url>" "<authorization 標頭值>"`，成功會記到 `uploads.tsv`。

上傳後約 1 小時內沒放進頁面就會失效，而且對話可能中斷，所以**每 8 句一輪**：
1. 一次呼叫 8 個 `notion-create-file-upload`（一次超過 10 個容易整批中斷）。
2. 一個 bash 指令依序跑 8 次 `upload.sh`。
3. `render.py "<工作資料夾>" <d> --chunk <k>` 只產生這 8 句（chunk 0 是頁首流程），馬上 `insert_content` 接到頁面。
這樣中斷時最多只損失 8 個未用的上傳。`uploads.tsv` 裡的 id 若已過期（隔天繼續），先把檔案改名再重新上傳。

## 6. 建 Notion 頁面
- 位置：預設放在「英文筆記」（`1fa144c0c788803b8c9ad02c074b84e8`）底下，先建總覽頁 `<片名>｜<N> 天跟讀計畫`（影片連結、每天句數對照表、各天頁面連結、被排除的句子清單），每天的頁面建在總覽頁底下。使用者指定別處就照做。
- 每天：`py -3.13 scripts/render.py "<工作資料夾>" <d>` 產生 `out\day<d>_chunk0..K.md` 並印出頁面標題。用 `notion-create-pages` 以 chunk0 建頁，其餘 chunk 依序用 `notion-update-page` 的 `insert_content` 接在後面（一次塞整頁會太大）。
- 最後一天：`render.py "<工作資料夾>" review` → `out\review.md`。
- 流程裡提到的「✍️ 造句口說紀錄」資料庫是共用的（`d8c2cbdb50c648b48e5b2b90b7e9550f`），要換就加 `--db <網址>`。
- Notion 偶爾回 500（Cross-cell memcached…）或 429：等幾秒重試即可。
- 之後要改已存在的音檔區塊：fetch 顯示的是 `notion-file-block://AAAA/BBBB?space_id=SSSS&name=NAME.mp3`，但 `update_content` 的 old_str 要寫成
  `<audio src="file://%7B%22source%22%3A%22attachment%3ABBBB%3ANAME.mp3%22%2C%22permissionRecord%22%3A%7B%22table%22%3A%22block%22%2C%22id%22%3A%22AAAA%22%2C%22spaceId%22%3A%22SSSS%22%7D%7D"></audio>` 才對得上。

## 7. 驗證和回報
- 重新 fetch Day 1 和最後一個學習日，確認句數、每句都有 `<audio>`。
- 回報：總覽頁連結、每天句數、被排除的句子、`conf` 偏低需要使用者聽一下的句子（附 Day 和句號）。
- 明說沒辦法驗證的事：我聽不到聲音，原音是否和文字對齊要使用者抽幾句確認。

## 選用
- 點字發音板（https://a50134.github.io/word-speaker/）目前只收錄 Phineas and Ferb S1E1。`render.py "<工作資料夾>" board` 會產生同格式的 `out\days.json`；要讓發音板支援新影片得另外改發音板，使用者要求時再做，做了以後 render 加 `--board "<網址>?day={d}"` 就會把嵌入框放進每日頁。
- 單字表：使用者要求時，比照「📚 單字表」資料庫（`d0a489fa14174c16b589a11051729e45`）的欄位新增。
