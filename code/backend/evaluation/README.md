# 搜尋品質評估（Precision@5）

本資料夾是 Term Project I 的搜尋品質評估：用 10 題固定查詢，對每題前 5 筆結果做人工相關性標註，計算 Precision@5（P@5）。

## 結果摘要

評估對象：`data/index-pg18.json`（PostgreSQL 18 文件，250 頁、8,087 個詞）。

| id | 查詢 | P@5 | 相關 / 回傳 |
|---|---|---|---|
| q01 | window functions | 0.40 | 2/5 |
| q02 | recursive common table expressions | 0.20 | 1/5 |
| q03 | transaction isolation levels | 0.40 | 2/5 |
| q04 | explicit table locks | 0.20 | 1/5 |
| q05 | how to get inserted rows back | 0.00 | 0/5 |
| q06 | array functions and operators | 0.20 | 1/5 |
| q07 | create view | 0.20 | 1/5 |
| q08 | reclaim storage from dead rows | 0.40 | 2/5 |
| q09 | sort rows order by | 0.20 | 1/5 |
| q10 | retry after serialization failure | 0.20 | 1/5 |
| | **平均** | **0.240** | |

分布：6 題 0.20、3 題 0.40、1 題 0.00，沒有任何一題超過 0.40。完整的每題前 5 名見 `review.md`，標註與理由見 `judgments.csv`。

## 評估方法

- **指標**：P@5 = 前 5 名中相關頁面數 ÷ 5。結果不足 5 筆時，缺的名額視為不相關（分母固定為 5，見 `metrics.py`）。
- **查詢集**：`queries.json` 共 10 題，依頁面主題撰寫，不是看搜尋結果調整的。其中 q05、q08 刻意用自然語言描述需求，檢驗詞彙不一致（vocabulary mismatch）時的表現。查詢集的 `status` 為 `frozen`，標註後不再修改。
- **相關性標註**：人工逐筆標 0 / 1，規則寫在 `queries.json` 的 `relevance_rule`：頁面「主要在談」該資訊需求才算相關（1）；只在語法列表或內文順帶提到查詢詞的頁面算不相關（0）；文件版本不同不影響判定。每一筆都在 `judgments.csv` 的 `reason` 欄寫了理由。
- **可重現性**：`run_info.json` 記錄評估時索引檔與查詢檔的 sha256，用來確認結果對應的是哪一份索引、哪一份查詢集。

## 弱查詢分析

以下是對照 `judgments.csv` 與索引統計（df、idf）整理的觀察。「可能原因」是從資料推測的解釋，沒有另外做消融實驗驗證。

### q05：how to get inserted rows back（P@5 = 0.00）

- 需求：INSERT / UPDATE / DELETE 的 `RETURNING` 子句。
- 前處理後的查詢詞是 how、get、inserted、rows、back（to 被停用字移除）。這些都是常見詞：df 介於 27 到 78 頁，idf 在 2.16 到 3.19 之間。
- 查詢裡沒有出現 `returning` 這個詞。這個詞在索引中有 29 頁，但查詢詞袋裡根本沒有它，純詞彙比對的 TF-IDF 不會知道「get inserted rows back」指的是 `RETURNING`。
- 結果：前 5 名是 SELECT、Data Manipulation 章節、ROLLBACK PREPARED 等，只是剛好包含 rows、inserted 之類的字，分數都很低（最高 0.1116）。
- 可能原因：詞彙不一致。這是詞袋模型的本質限制，不是實作錯誤。

### q02：recursive common table expressions（P@5 = 0.20）

- 需求：`WITH` / `WITH RECURSIVE`。
- 第 1 名正確（7.8 WITH Queries，0.2019），但第 2 到 5 名是 DROP TABLE、CREATE TABLE AS、11.7 Indexes on Expressions、SELECT INTO，分數都在 0.18 到 0.19，和第 1 名差距很小。
- 查詢詞 table 出現在 133 頁（idf 1.63），expressions 出現在 37 頁。許多不相關的語法頁因為 table 出現次數很高，或有 expression 字樣，累積出接近的分數。
- 觀察：前 5 名裡的錯誤多半是命中通用詞（table、expressions），而不是命中專有詞 recursive（只有 15 頁）。
- 可能原因：原始詞頻缺少飽和處理，通用詞反覆出現會增加該詞對分數的貢獻。BM25 改變了這題的前五名組成，P@5 仍為 0.20。 [BM25 比較報告](bm25/report.md)

### 其他低分題的共同現象

- q07（create view）：前 5 名都是 VIEW 相關頁面（DROP VIEW 0.7339 排在 CREATE VIEW 0.7211 前面），但只有 CREATE VIEW 本身符合「如何定義 view」的需求，其餘算不相關。這是 `view` 一詞在這些頁面都大量出現造成的，屬於指令頁之間難以區分。
- q09、q10、q04：第 1 名通常是對的或接近對的，後面幾名混入通用頁面（Window Functions、CREATE TABLE AS 等），分數很低。

## 限制

- 只有 10 題、每題只看前 5 名，每題 P@5 的最小單位是 0.20，平均值的雜訊不小，適合用來比較改版前後，不適合當成絕對品質的結論。
- TF-IDF 基準標註由單人完成，沒有做標註者間一致性檢查。
- 沒有計算召回率（Recall），因為沒有標出每題「所有」相關頁面。

## 重現步驟

在 `code/backend` 目錄執行：

```bash
# 1. 用預設索引（data/index-pg18.json）跑查詢，輸出前 5 名供人工標註。
#    若 judgments.csv 已存在，加 --force 會覆蓋人工標註，請謹慎。
python -m evaluation.run_queries --force

# 2. 在 judgments.csv 的 relevant 欄填 1 / 0，reason 欄寫理由

# 3. 計算 P@5，輸出 results.md 與 results.csv
python -m evaluation.compute_metrics
```

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `queries.json` | 10 題固定查詢、需求描述與相關性規則 |
| `judgments.csv` | 每題前 5 名的人工標註（relevant 0/1 與理由） |
| `results.md` / `results.csv` | 每題 P@5 與平均 |
| `review.md` | 每題前 5 名的可讀清單 |
| `run_info.json` | 索引檔與查詢檔的 sha256，用於重現 |
| `metrics.py` | P@5 與去重頁數的計算函式 |
| `run_queries.py` | 跑查詢並產生待標註檔案 |
| `compute_metrics.py` | 由標註計算指標 |

## BM25 加分比較

在 `IRandGAI` 環境下，從 `code/backend` 執行：

```powershell
python -m evaluation.compare_bm25 prepare
```

命令使用 `data/index-pg18.json` 與固定的 `queries.json`，依 `run_info.json` 驗證快照並核對 TF-IDF 前五名。兩個排序共用 `judgments.csv` 中相同查詢及文件的判定。BM25 新出現的文件列在 [補充判定清單](bm25/new_judgments.csv)，重跑 `prepare` 會保留現有清單。

請依文件全文逐筆複核 `relevant` 和 `reason`，必要時更正後，把該筆 `status` 從 `draft` 或 `pending` 改成 `confirmed`。全部複核後執行：

```powershell
python -m evaluation.compare_bm25 compare
```

有缺漏時，命令會列出待確認的查詢與文件 ID。成功後會在 `evaluation/bm25/` 產出 [rankings.csv](bm25/rankings.csv)（兩種排序的前五名、分數與判定）及 [comparison.csv](bm25/comparison.csv)（逐題及平均 P@5 與差值）。本次補充判定已確認，可直接執行 `compare` 重現 [BM25 比較報告](bm25/report.md) 的結果。
