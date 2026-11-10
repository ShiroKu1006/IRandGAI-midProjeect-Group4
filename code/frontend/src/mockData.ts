import type { SearchResponse } from './api.ts'

// 假資料：僅供前端開發時預覽畫面，分數是簡化的示意，不是真正的 TF-IDF 餘弦相似度。
type MockDoc = {
  docId: number
  title: string
  url: string
  text: string
}

const MOCK_DOCS: MockDoc[] = [
  {
    docId: 1,
    title: 'Introduction to Information Retrieval',
    url: 'https://example.com/ir/intro',
    text: 'Information retrieval is the task of finding documents that satisfy an information need from a large collection. A search engine builds an inverted index so that queries can be answered without scanning every document.',
  },
  {
    docId: 2,
    title: 'Inverted Index Explained',
    url: 'https://example.com/ir/inverted-index',
    text: 'An inverted index maps each term to a postings list containing document ids and term frequencies. The index is built once offline and loaded when the search service starts.',
  },
  {
    docId: 3,
    title: 'TF-IDF Weighting',
    url: 'https://example.com/ir/tf-idf',
    text: 'TF-IDF weights a term by how often it appears in a document and how rare it is across the collection. Documents and queries share the same vocabulary and idf values.',
  },
  {
    docId: 4,
    title: 'Cosine Similarity for Ranking',
    url: 'https://example.com/ir/cosine',
    text: 'Cosine similarity compares the angle between the query vector and each document vector. Document norms are precomputed so that ranking only needs the postings of the query terms.',
  },
  {
    docId: 5,
    title: 'Web Crawler Basics',
    url: 'https://example.com/crawler/basics',
    text: 'A web crawler starts from seed urls, follows links inside an allowlist of hosts, respects robots.txt, and waits at least two seconds between requests to the same host.',
  },
  {
    docId: 6,
    title: 'Evaluating Search with Precision at K',
    url: 'https://example.com/eval/precision-at-k',
    text: 'Precision at five is the number of relevant documents among the first five results divided by five. Missing results count as not relevant and the denominator stays five.',
  },
  {
    docId: 7,
    title: 'Text Preprocessing and Tokenization',
    url: 'https://example.com/ir/preprocessing',
    text: 'Preprocessing lowercases text, splits it into tokens, and removes stopwords. Hyphenated words such as machine-learning should be split into separate tokens instead of being merged.',
  },
  {
    docId: 8,
    title: 'BM25 Ranking Function',
    url: 'https://example.com/ir/bm25',
    text: 'BM25 is a ranking function that improves on plain TF-IDF with term frequency saturation and document length normalization. It is a common baseline for search engines.',
  },
]

export const mockIndexedCount = MOCK_DOCS.length

function tokenize(text: string): string[] {
  return text.toLowerCase().match(/[a-z0-9+#]+/g) ?? []
}

export function mockSearch(query: string): SearchResponse {
  const queryTerms = tokenize(query)
  const results = MOCK_DOCS.map((doc) => {
    const words = tokenize(`${doc.title} ${doc.text}`)
    const hits = words.filter((word) => queryTerms.includes(word)).length
    return { doc, score: hits / Math.sqrt(words.length) }
  })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)
    .map(({ doc, score }) => ({
      title: doc.title,
      url: doc.url,
      snippet: doc.text,
      score,
    }))

  return { query, indexedCount: mockIndexedCount, results }
}
