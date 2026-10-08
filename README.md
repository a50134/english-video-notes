# english-video-notes

Claude Code 的 skill：貼上英文影片網址，自動下載音檔和字幕、逐句對時剪出原音，寫中文翻譯與文法筆記，排成 N 天跟讀（shadowing）計畫建到 Notion。

## 目的

把「找字幕 → 斷句 → 剪每句原音 → 寫筆記 → 建 Notion 頁面」這串手工流程變成一個指令。每天一頁，內容有流程打勾清單和逐句的英文、中文、原音、文法、例句、我的造句欄；最後一天是總複習。

## 使用技術

- Python 3.13
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)：下載音檔和字幕
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（small.en）：取得每個字的時間，用來對時
- imageio-ffmpeg 內附的 ffmpeg：轉檔和剪音檔
- Notion 連接器（MCP）：上傳音檔、建立頁面

## 內容

| 檔案 | 說明 |
|---|---|
| `SKILL.md` | 給 Claude 的完整流程說明 |
| `scripts/check.py` | 檢查需要的套件和模型在不在，不會安裝任何東西 |
| `scripts/fetch.py` | 從網址或本機檔案取得 `audio.mp3`、字幕和 `meta.json` |
| `scripts/segment.py` | 語音辨識、斷句、對時，產生 `sentences.json` |
| `scripts/plan.py` | 把句子分配到各天並剪出每句音檔 |
| `scripts/render.py` | 產生每天的 Notion 頁面內容 |
| `scripts/upload.sh` | 把一個音檔送到 Notion 的檔案上傳 |
| `scripts/common.py` | 共用路徑和小工具 |

## 安裝與使用

1. 把這個資料夾放到 `~/.claude/skills/english-video-notes`。
2. 安裝套件到腳本會找的位置：

```bash
py -3.13 -m pip install yt-dlp
py -3.13 -m pip install --target "%LOCALAPPDATA%\english-video-notes\deps" faster-whisper imageio-ffmpeg numpy
```

3. 在 Claude Code 貼上影片網址並說「做成 Notion 筆記」，或輸入 `/english-video-notes <網址>`。

語音模型（約 460 MB）會在第一次執行 `segment.py` 時從 Hugging Face 下載到 `%LOCALAPPDATA%\english-video-notes\models`。

## 備註

- 影片和音檔有版權，只供個人學習：音檔只留在本機和自己的 Notion，不要公開散布。
- `SKILL.md` 和 `render.py` 裡寫了作者自己的 Notion 頁面 ID 和本機路徑，別人使用前要換成自己的。
- 只在 Windows 11 上用過。
