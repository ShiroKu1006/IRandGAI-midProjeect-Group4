# BM25 與 TF-IDF 餘弦排序比較

## 一、實驗設定

我們用原本的 250 篇 PostgreSQL 18 文件和 10 題固定查詢來比較。標題和正文的前處理、倒排索引都沿用原本的設定，只換排序的計分方式。Precision@5 的算法是把每題前 5 名的相關文件數除以 5，最後再算 10 題的平均。

### BM25 計算方式

原本的做法是用原始詞頻乘上平滑後的 IDF，再算查詢和文件的餘弦相似度。BM25 會看詞出現了幾次，但同一個詞一直出現，後面每多出現一次的加分會越來越小。文件長度也會影響分數。這次用 $k_1=1.2$、$b=0.75$，把斷詞後不重複的查詢詞各算一次，再將分數加起來。

$$
\operatorname{BM25}(q,d) =
\sum_{t \in \operatorname{unique}(q)}
\ln\!\left(1 + \frac{N-df_t+0.5}{df_t+0.5}\right)
\frac{tf_{t,d}(k_1+1)}
{tf_{t,d}+k_1(1-b+b\,dl_d/avgdl)}
$$

$N$ 是文件總數，$df_t$ 是有出現詞 $t$ 的文件數，$tf_{t,d}$ 則是這個詞在文件 $d$ 裡出現的次數。文件長度 $dl_d$ 用前處理後的詞數來算，這 250 篇的平均長度 $avgdl$ 是 816.768 詞。

### 相關性判定

我們看的是文件全文，主要在回答這題要找的資訊才算相關。同一題如果兩種方法都找到同一篇，就沿用同一個判定。BM25 前 5 名加起來共 50 筆，其中 25 筆原本就判過，剩下 25 筆也照同樣的規則補標，再由組員確認。

## 二、實驗結果

兩種方法的平均 P@5 都是 **0.240**。逐題來看，BM25 在 q04 和 q08 的前 5 名各多了 1 篇相關文件，但 q06 和 q09 各少了 1 篇，剛好抵銷。其他 6 題的 P@5 相同。

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

這題是想查有哪些表鎖模式，以及 `LOCK` 指令要怎麼用。兩種方法的第 1 名都是 Explicit Locking，差別在於 BM25 的第 5 名還有一篇 `LOCK` 指令頁。這頁有 `table` 和 `locks`，長度 807 詞，也跟平均長度差不多。看內容時，可以直接查到 `LOCK TABLE` 的語法、表鎖模式和 `NOWAIT`，所以這篇算相關。 [Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html) · [LOCK](https://www.postgresql.org/docs/18/sql-lock.html)

### q06 — array functions and operators

TF-IDF 的第 1 名是 Arrays，到了 BM25 卻排到第 9 名。BM25 排第 1 的 JSON Functions and Operators 也有 `array`、`functions`、`operators` 這些字，但它講的是 JSON 陣列。這題要找的是 PostgreSQL 原生陣列的函式和運算子，所以這篇不算相關。BM25 的前 5 名都沒有符合這個需求。 [Arrays](https://www.postgresql.org/docs/18/arrays.html) · [JSON Functions and Operators](https://www.postgresql.org/docs/18/functions-json.html)

### q05 — how to get inserted rows back

如果還不知道可以用 `RETURNING`，可能就會像這題一樣，直接搜「怎麼拿回剛新增的資料列」。BM25 的第 2 名 CREATE POLICY 有提到 `RETURNING`，但那段在講權限和資料列層級政策。兩種方法的前 5 名都沒找到主要在說明怎麼用 `RETURNING` 取回異動資料列的頁面。 [CREATE POLICY](https://www.postgresql.org/docs/18/sql-createpolicy.html)

## 四、結論

這次只測了這 10 題和一份文件快照。兩種計分方式裡，IDF、詞頻和文件長度的處理都有差，所以目前只能看出換成 BM25 後排名怎麼變，還看不出是哪一項影響最大。
