# BM25 與 TF-IDF 餘弦排序比較

## 一、實驗設定

- 資料集共 250 篇 PostgreSQL 18 文件
- 查詢共 10 題，兩種方法使用同一組查詢
- 評估指標為 Precision@5，將每題前 5 名的相關文件數除以 5，再取 10 題的平均

兩種方法共用標題和正文的前處理結果，也使用同一份倒排索引。TF-IDF 用原始詞頻乘上平滑後的 IDF，再算查詢和文件之間的餘弦相似度。BM25 也會用到詞頻和文件頻率，詞出現越多次，每多一次帶來的分數會逐漸變小，分數也會依文件長度調整。

### BM25 計算方式

這次固定 $k_1=1.2$、$b=0.75$，每個查詢詞只算一次，再把分數加起來。

$$
\operatorname{BM25}(q,d) =
\sum_{t \in \operatorname{unique}(q)}
\ln\!\left(1 + \frac{N-df_t+0.5}{df_t+0.5}\right)
\frac{tf_{t,d}(k_1+1)}
{tf_{t,d}+k_1(1-b+b\,dl_d/avgdl)}
$$

$N$ 是索引中的文件數，$df_t$ 是包含詞 $t$ 的文件數，$tf_{t,d}$ 是詞 $t$ 在文件 $d$ 出現的次數。$dl_d$ 是文件前處理後的詞數，這次的平均文件長度 $avgdl$ 為 816.768 詞。

### 相關性判定

同一題如果搜到同一份文件，就共用原本的判定。BM25 的 50 筆結果中有 25 筆可以沿用 TF-IDF 的人工判定，另外 25 筆採用組員確認的補充判定。我們依索引快照中的全文判斷，頁面的主要內容有回答這題要找的資訊才算相關。

## 二、實驗結果

兩種方法的平均 P@5 都是 **0.240**。分開看每題，BM25 在 q04 和 q08 各多找到 1 篇相關文件，在 q06 和 q09 各少 1 篇，其他 6 題的 P@5 相同。

| 題號 | 查詢 | TF-IDF P@5 | BM25 P@5 | 差值 |
| --- | --- | ---: | ---: | ---: |
| q01 | window functions | 0.40 | 0.40 | 0.00 |
| q02 | recursive common table expressions | 0.20 | 0.20 | 0.00 |
| q03 | transaction isolation levels | 0.40 | 0.40 | 0.00 |
| q04 | explicit table locks | 0.20 | 0.40 | +0.20 |
| q05 | how to get inserted rows back | 0.00 | 0.00 | 0.00 |
| q06 | array functions and operators | 0.20 | 0.00 | −0.20 |
| q07 | create view | 0.20 | 0.20 | 0.00 |
| q08 | reclaim storage from dead rows | 0.40 | 0.60 | +0.20 |
| q09 | sort rows order by | 0.20 | 0.00 | −0.20 |
| q10 | retry after serialization failure | 0.20 | 0.20 | 0.00 |
| | **平均** | **0.240** | **0.240** | **0.000** |


## 三、查詢結果分析

### q04 — explicit table locks

兩種方法的第 1 名都是 Explicit Locking。BM25 還把 `LOCK` 指令頁排在第 5 名。這頁包含 `table` 和 `locks`，長度是 807 詞，接近文件的平均長度。從內容來看，這頁有說明 `LOCK TABLE` 的語法、表鎖模式和 `NOWAIT`，因此前 5 名的相關文件從 1 篇增加到 2 篇。 [Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html) · [LOCK](https://www.postgresql.org/docs/18/sql-lock.html)

### q06 — array functions and operators

這題想找 PostgreSQL 原生陣列的函式和運算子。Arrays 在 TF-IDF 排第 1 名，在 BM25 掉到第 9 名。BM25 的第 1 名是 JSON Functions and Operators，這頁同時出現 `array`、`functions`、`operators`，但頁面介紹的是 JSON 陣列，所以判定為不相關。這題的 BM25 前 5 名沒有相關文件。 [Arrays](https://www.postgresql.org/docs/18/arrays.html) · [JSON Functions and Operators](https://www.postgresql.org/docs/18/functions-json.html)

### q05 — how to get inserted rows back

這題要找的是用 `RETURNING` 取回異動的資料列，但查詢字串沒有用到 `returning`。BM25 第 2 名是 CREATE POLICY，裡面雖然有提到 `RETURNING`，主要在說明權限和資料列層級政策。兩種方法的前 5 名都沒有找到以 `RETURNING` 取回資料列為主題的頁面。 [CREATE POLICY](https://www.postgresql.org/docs/18/sql-createpolicy.html)

## 四、結論

這次的結果只涵蓋這 10 題和同一份文件快照。實驗直接比較兩種完整的計分方式，因此還無法判斷 IDF、詞頻飽和或長度正規化各自造成多少影響。
