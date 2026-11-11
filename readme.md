# 資訊檢索與生成式人工智慧：期中小組專題

本專題使用 React + TypeScript + Vite 開發前端，Flask 提供後端 API，Python 環境使用 Conda 管理，名稱統一為 `IRandGAI`。

小組共用開發規範見 [docs/guidelines.md](docs/guidelines.md)，涵蓋架構、模組分工、程式風格與驗證要求；Codex 與 Claude Code 的入口分別為根目錄的 `AGENTS.md` 與 `CLAUDE.md`。

前後端專案已經建立好。取得 repository 後，依照以下步驟安裝相依套件即可，不需要重新執行 `create-vite` 或建立 React 專案。

## 開始前先準備

- Git：用來取得及同步專案。
- Node.js：建議使用 **22.19.0 或更新的 22.x 版本**，npm 會隨 Node.js 安裝。
- Conda：Anaconda 或 Miniconda 皆可，並確認 PowerShell 能使用 `conda`。

先在 PowerShell 確認工具可以正常執行：

```powershell
git --version
node --version
npm.cmd --version
conda --version
```

以下命令以 Windows PowerShell 為例。請先進入你電腦上的 **repository 根目錄**，也就是包含這份 `readme.md` 與 `code` 資料夾的位置，不需要使用其他組員電腦的絕對路徑。

```text
project1/
├── readme.md
├── 題目/
└── code/
    ├── frontend/           # React + TypeScript + Vite
    │   ├── package.json
    │   └── package-lock.json
    └── backend/            # Flask API
        ├── app.py
        └── environment.yml
```

## 前端：第一次安裝與啟動

在 repository 根目錄開啟第一個 PowerShell 終端機：

```powershell
cd code/frontend
npm.cmd ci
npm.cmd run dev
```

- `npm.cmd ci` 依照 `package-lock.json` 安裝套件，讓大家使用一致的版本。
- 使用 `npm.cmd` 可以避免 PowerShell 執行原則阻擋 `npm.ps1`。
- 啟動後開啟終端機顯示的網址，預設通常是 `http://localhost:5173`；若連接埠已被占用，以實際顯示的網址為準。
- 保持這個終端機運作，按 `Ctrl+C` 可停止前端。

目前 TypeScript 固定為 `6.0.3`，與專案使用的 `typescript-eslint` 相容。請直接使用 lockfile 安裝，不要自行升級成 TypeScript 7，或加上 `--force`、`--legacy-peer-deps` 略過相依套件檢查。

## 後端：第一次建立 Conda 環境與啟動

另外開啟第二個 PowerShell 終端機，從 repository 根目錄開始。

### 1. 建立並啟用環境

```powershell
cd code/backend
conda env create -f environment.yml
conda activate IRandGAI
```

`environment.yml` 已指定環境名稱 `IRandGAI`、Python 3.12 與 Flask。Conda 若詢問是否繼續安裝，輸入 `y`。啟用後，終端機前方應顯示 `(IRandGAI)`。

如果電腦已經有 `IRandGAI` 環境，跳過建立步驟，在 `code/backend` 改用以下命令同步需求：

```powershell
conda env update --name IRandGAI -f environment.yml
conda activate IRandGAI
```

確認目前使用的 Python 與 Flask：

```powershell
python --version
python -c "import sys; print(sys.executable)"
python -m flask --version
```

Python 應為 3.12.x，執行檔路徑應指向 `IRandGAI` 環境。

### 2. 啟動 Flask

接續上一步，目前已位於 `code/backend`：

```powershell
python -m flask --app indexed_app:create_indexed_app run --debug
```

開啟 `http://127.0.0.1:5000/api/health`，預期會收到：

```json
{"status": "ok"}
```

這個端點用來確認後端服務已啟動。搜尋 API 可用 `/api/search?q=VACUUM` 測試。

保持後端終端機運作，按 `Ctrl+C` 可停止服務。`--debug` 用於本機開發，修改程式後會自動重新載入。

## 之後每天開發怎麼啟動

安裝完成後，通常不需要每天重裝套件。前後端各使用一個終端機，以下仍從 repository 根目錄開始。

前端終端機：

```powershell
cd code/frontend
npm.cmd run dev
```

後端終端機：

```powershell
conda activate IRandGAI
cd code/backend
python -m flask --app indexed_app:create_indexed_app run --debug
```

Vite 會將 `/api` 代理至 `http://127.0.0.1:5000`。在前端網址輸入查詢即可展示。

## PostgreSQL 18 語料與新版 demo

爬蟲只追蹤 `www.postgresql.org` 的 `/docs/18/`，重新導向也必須在範圍內。種子網址為 `https://www.postgresql.org/docs/18/` 加上下列頁面檔名。

- `sql-commands.html`、`datatype.html`
- `sql-createtable.html`、`ddl-constraints.html`、`datatype-json.html`
- `transaction-iso.html`、`tutorial-window.html`、`sql-vacuum.html`

從 `code/backend` 重爬時，使用尚未存在的檔名，例如：

```powershell
conda activate IRandGAI
python crawler.py --db data/documents-pg18-next.db --max-documents 250
if ($LASTEXITCODE -eq 0) {
    python indexer.py --db data/documents-pg18-next.db --out data/index-pg18-next.json
}
```

爬蟲保留正規化 URL 唯一約束，並略過空白正規化後完全相同的正文。爬取摘要在同名的 `.crawl.log` 檔案末尾。有效頁不足 200 筆或缺少任一種子時，爬蟲以錯誤狀態結束，應先檢查紀錄再換新檔名重爬。

新版交付快照為 `data/documents-pg18.db`、`data/index-pg18.json` 和 `data/documents-pg18.crawl.log`。搜尋 API 與評估預設使用新版索引，SQLite 預覽、資料庫檢查與建索引預設讀取新版資料庫。從 `code/backend` 啟動：

```powershell
python -m flask --app indexed_app:create_indexed_app run --port 5000
```

<<<<<<< HEAD
簡報要比較舊版時，先停止 Flask，再設定 `$env:SEARCH_INDEX_PATH = 'data/index.json'` 並重新啟動。要恢復新版預設，清除該環境變數後重新啟動。舊版 SQLite 位於 `data/documents.db`。比較時可用 `CREATE TABLE`、`jsonb`、`window functions` 看收錄與排名差異。
=======
舊版索引（`data/index.json`）已移除，預設索引改為 `data/index-pg18.json`，不需再設定 `SEARCH_INDEX_PATH`。舊版 SQLite 仍保留在 `data/documents.db`；下方「快照比較」表保留當時的名次紀錄。
>>>>>>> ddb3a5f378e340e7790e764e2a13c960d574807b

### 快照比較

新版收錄 250 篇 PostgreSQL 18 文件，8 個種子全數收錄。以相同的 TF-IDF 餘弦排序比較兩版索引，對應專頁的名次如下。

| 查詢 | 對應專頁 | 舊版 | 新版 |
| --- | --- | ---: | ---: |
| `CREATE TABLE` | CREATE TABLE | 未收錄 | 6 |
| `foreign key constraint` | Constraints | 未收錄 | 2 |
| `transaction isolation` | Transaction Isolation | 3 | 2 |
| `jsonb` | JSON Types | 未收錄 | 1 |
| `window functions` | Window Functions | 1 | 1 |
| `VACUUM` | VACUUM | 1 | 1 |

舊版的 `window functions` 前十筆都是同一篇的不同版本，新版前十筆各自對應不同頁面。`CREATE TABLE` 新版第一筆是 `CREATE TABLE AS`，反映餘弦排序仍會把共用詞彙較多的文件排在前面。這張表記錄指定專頁名次，供 demo 比較。

## 搜尋品質評估

固定查詢、人工相關性判定、TF-IDF 基準結果與 BM25 比較的重現步驟，見 [評估 README](code/backend/evaluation/README.md)。

## 前端檢查

在 `code/frontend` 目錄執行：

```powershell
npm.cmd run build
npm.cmd run lint
```

- `build`：執行 TypeScript 編譯檢查並建置前端，產出放在 `dist`。
- `lint`：執行 ESLint，檢查完成後若沒有違規訊息並回到命令提示字元，即表示通過。

## 小組同步與環境檔維護

- 前端修改套件時，將 `package.json` 與 `package-lock.json` 一起提交 Git。其他組員拉取更新後，在 `code/frontend` 重新執行 `npm.cmd ci`。
- 後端套件安裝前，先確認已啟用 `IRandGAI`。新增需求時，同步更新並提交 `environment.yml`。
- `node_modules`、`dist`、Python 環境目錄及 `__pycache__` 不應提交 Git。

其他組員拉取後端環境檔更新後，在 `code/backend` 執行：

```powershell
conda env update --name IRandGAI -f environment.yml
conda activate IRandGAI
```

若要從本機環境重新匯出需求，在 `code/backend` 執行以下命令。這會更新現有的 `environment.yml`，提交前請確認差異：

```powershell
conda env export --name IRandGAI --from-history |
    Where-Object { $_ -notmatch '^prefix:' } |
    Set-Content -Encoding utf8 environment.yml
```

請確認匯出內容的 `name` 是 `IRandGAI`，且 `dependencies` 包含 Python 3.12 與 Flask。`--from-history` 只匯出透過 Conda 明確安裝的套件需求，不會鎖定全部間接相依版本；未來若改用 pip 安裝套件，需要另外記錄這些需求。

## 常見問題

| 狀況 | 處理方式 |
| --- | --- |
| 找不到 `conda` | 改用 Anaconda／Miniconda 提供的 PowerShell Prompt，再確認 `conda --version`。 |
| 顯示 `No module named flask` | 確認已執行 `conda activate IRandGAI`，再用 `conda install flask` 安裝。 |
| 前端出現 `ERESOLVE` | 先確認使用 repository 內的 `package.json` 與 lockfile，並以 `npm.cmd ci` 安裝；不要略過版本相容性檢查。 |
| Flask 顯示找不到 `app` | 確認目前位於 `code/backend`，且該目錄內有 `app.py`。 |
| 前端啟動網址不是 5173 | 使用 Vite 終端機實際顯示的網址。 |
