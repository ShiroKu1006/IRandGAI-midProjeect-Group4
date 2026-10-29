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
python -m flask --app app run --debug
```

開啟 `http://127.0.0.1:5000/api/health`，預期會收到：

```json
{"status": "ok"}
```

這個端點用來確認後端服務已啟動。直接開啟 `/` 目前會得到 404，因為程式只設定了 `/api/health` 路由。

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
python -m flask --app app run --debug
```

目前 Vite 尚未設定 `/api` 代理，前端也尚未串接 Flask。兩個服務都能啟動，只代表各自的基本環境正常；後端先透過 `/api/health` 獨立確認。

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
