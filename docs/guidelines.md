# Repository Guidelines

本文件是組員、Codex 與 Claude Code 共用的 repository 規範；文中路徑皆相對於 repository 根目錄。規範變更統一更新本文件，根目錄的 `AGENTS.md` 與 `CLAUDE.md` 僅保留讀取入口。

## 專案結構與模組分工

本專案為資訊檢索與生成式人工智慧課程的**小組網頁搜尋引擎專題**。作業要求以 `題目/termProjectI_Web_Search_Engine.zh-TW.txt` 為依據，環境設定見 `readme.md`。

- `code/frontend/`：React、TypeScript 與 Vite；`src/` 放元件與樣式，`src/assets/` 放匯入的圖片，`public/` 放直接提供的靜態資源。
- `code/backend/`：Flask API；`app.py` 定義路由，`environment.yml` 管理 Conda 環境。
- `題目/`：作業規格與文字版本。

目前前端仍是 Vite 模板。後端提供 `/api/health`、`/api/search` 與記憶體搜尋核心，正式 SQLite 資料與離線索引尚待串接。

## 架構與協作邊界

- **離線流程**：以 PostgreSQL 官方文件為搜尋語料，爬取後存入 SQLite，再做前處理並產出索引檔。文件欄位建議包含 `doc_id`、`url`、`title`、`text`、`fetch_time`。
- **查詢流程**：React → Flask API → 搜尋核心 → 既有索引與資料集。啟動時載入索引，不在查詢期間爬取、重建索引或重新擬合 IDF。
- **模組分工**：`app.py` 負責 API，`search.py` 負責查詢排序。爬蟲、離線建索引、共用前處理及評估各自拆分。文件與查詢共用前處理，API 與評估共用搜尋核心。
- **索引交付**：離線建索引從 SQLite 文件產出倒排索引與文件集合統計。交付時須對齊穩定的 `doc_id`、共用前處理、TF／IDF 定義、postings（詞對應文件 ID 與詞頻）、文件頻率和文件向量 L2 範數。正式 SQLite 欄位及索引檔格式待資料集、索引與搜尋負責人確認。
- **搜尋介面**：`SearchIndex` 接收同一份索引快照的文件、postings、IDF、文件範數及前處理函式。`search(query, top_k=10)` 回傳 `(indexed_count, hits)`，核心結果保留 `doc_id` 供評估使用。現階段核心以原始詞頻乘上交付的 IDF 計算權重。測試專用斷詞為小寫英數及底線，測試 IDF 為 `ln((N+1)/(df+1))+1`。正式前處理與權重定義仍待組員對齊。

小組依爬蟲、索引、搜尋／API、前端／評估分工，相關性判定共同參與。先完成必做檢索流程與本機展示，再考慮 BM25 等加分項目。

## 搜尋 API 契約

前端呼叫 `GET /api/search?q=SQL`。`q` 為必填的查詢字串，應做 URL 編碼。後端去除查詢的首尾空白後再驗證與搜尋。開發期間可先使用下列 JSON 範例。

**有命中（`200`）**。 `indexed_count` 是索引涵蓋的文件總數。`results` 最多包含 10 筆正分結果，依分數由高到低排列，同分依 `doc_id` 升冪。每筆結果包含 `title`、`url`、純文字 `snippet` 和數值 `score`。摘要合併連續空白後取前 160 字元。

```json
{
  "indexed_count": 3,
  "results": [
    {
      "title": "PostgreSQL Indexes",
      "url": "https://www.postgresql.org/docs/18/indexes.html",
      "snippet": "Indexes can help retrieve rows faster.",
      "score": 0.82
    }
  ]
}
```

**未命中（`200`）**

```json
{"indexed_count": 3, "results": []}
```

**缺少 `q` 或去除首尾空白後為空字串（`400`）**

```json
{"error": "invalid_query"}
```

**有效查詢但搜尋核心尚未配置（`503`）**

```json
{"error": "search_unavailable"}
```

## 檢索與資料規範

倒排索引、TF-IDF 與餘弦排序須自行實作；不得以搜尋服務或 `TfidfVectorizer` 取代。記錄 TF／IDF 定義，查詢沿用文件集合的詞彙表與 IDF。

爬蟲須遵守主機白名單（含重新導向）、robots.txt、可識別的 User-Agent 與每主機至少兩秒間隔；設定逾時、嘗試上限並保留失敗紀錄。目標為 200–1,000 個有效、不重複且文字非空的公開 HTML 網頁。

搜尋最多回傳 10 筆正分結果，處理空白、詞彙表外及無結果查詢。介面顯示索引網頁數、標題、HTTP/HTTPS 連結、純文字摘要與分數，不直接渲染爬取的 HTML。

## 安裝、開發與建置命令

以下使用 Windows PowerShell。前端命令在 `code/frontend` 執行：

```powershell
npm.cmd ci           # 依 lockfile 安裝
npm.cmd run dev      # 啟動開發伺服器
npm.cmd run build    # TypeScript 檢查與建置，輸出 dist/
npm.cmd run lint     # 執行 ESLint
npm.cmd run preview  # 預覽已建置的前端
```

依 `readme.md` 使用 Node.js 22.19.0 以上的 22.x；TypeScript 固定為 6.0.3，勿任意升級或略過相依檢查。

後端命令在 `code/backend` 執行：

```powershell
conda env create -f environment.yml
conda activate IRandGAI
python -m flask --app app run --debug
```

既有環境以 `conda env update --name IRandGAI -f environment.yml` 同步，使用 Python 3.12。前後端各開一個終端機。

## 程式風格與命名

沿用現有風格：TypeScript 使用兩格縮排、單引號且省略分號；React 元件使用 PascalCase，變數與函式使用 camelCase。Python 使用四格縮排與 snake_case。新增程式依功能拆分，避免持續堆疊於 `App.tsx` 或 `app.py`。

前端以 `eslint.config.js` 的規則為準，目前未設定 Prettier 或 Python formatter。修改前端依賴時，同時更新 `package.json` 與 `package-lock.json`；後端依賴記錄於 `environment.yml`。

## 測試與驗證

前端變更執行 build、lint 並檢查畫面。後端測試使用標準函式庫 `unittest` 與 Flask test client。在 `IRandGAI` 環境中，從 `code/backend` 執行：

```powershell
python -m unittest discover -s tests -v
```

搜尋／API 的第一個里程碑先以固定結果驗證 HTTP 狀態碼與回應格式，再用 3～5 篇測試文件和一份可手算的小索引，讓 API 跑過候選篩選、TF-IDF 與餘弦排序。核對分數、排名、無結果和空白查詢。這兩步可在前端和正式 SQLite 資料就緒前完成。

啟動後端後，另開 PowerShell 驗證：

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

預期 `status` 為 `ok`。新增測試框架時，須同步記錄執行命令；建議前端使用 `*.test.tsx`，後端使用 `tests/test_*.py`。

品質評估須固定資料／索引快照及 10 個查詢，依文件全文人工判定相關性，保存排名、文件 ID／網址、標記與理由。Precision@5 分母固定為 5，缺少結果算不相關；回報各查詢與平均值，分析至少兩個失敗案例。資料、索引與評估產物的存放位置及重現命令須記入 README。

## Commit 與 Pull Request

現有提交如 `backend init`、`add readme`，採簡短英文描述，尚無強制前綴。新提交應聚焦單一變更，使用具體動詞，例如 `add search endpoint`。

PR 請描述目的、改後行為、驗證命令與結果，並連結相關 issue。介面變更附截圖；API／資料格式變更附範例與相容性影響，整合前同步相關組員。未完成的驗證須明列原因。

## 設定與敏感資訊

不得提交 `.env`、金鑰或含敏感資料的紀錄；設定範例使用不含真實憑證的 `.env.example`。不要新增追蹤 `node_modules/`、`dist/`、Conda 環境或 `__pycache__/` 等產物。Flask `--debug` 僅供本機開發。
