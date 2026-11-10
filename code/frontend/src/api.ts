import { mockSearch } from './mockData.ts'

export type SearchResult = {
  title: string
  url: string
  snippet: string
  score: number
}

export type SearchResponse = {
  query: string
  indexedCount: number
  results: SearchResult[]
}

// 後端契約（見 docs/guidelines.md「搜尋 API 契約」）：
// GET /api/search?q=...
//   200 -> { indexed_count, results: [{ title, url, snippet, score }] }
//   400 -> { error: 'invalid_query' }
//   503 -> { error: 'search_unavailable' }
type ApiSearchResponse = {
  indexed_count: number
  results: SearchResult[]
}

// 預設連到真實後端。只想看假資料畫面時：VITE_USE_MOCK=true npm run dev
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const MOCK_DELAY_MS = 200

const ERROR_MESSAGES: Record<string, string> = {
  invalid_query: '請輸入至少一個關鍵字。',
  search_unavailable: '後端的搜尋核心尚未就緒（還沒有載入索引）。',
}

function delay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { error?: string }
    if (data.error && data.error in ERROR_MESSAGES) {
      return ERROR_MESSAGES[data.error]
    }
  } catch {
    // 回應不是 JSON，改用下面的預設訊息
  }
  return `伺服器回應錯誤（HTTP ${response.status}），請確認後端 Flask 是否已啟動。`
}

export async function searchDocuments(
  query: string,
  signal: AbortSignal,
): Promise<SearchResponse> {
  if (USE_MOCK) {
    await delay(MOCK_DELAY_MS)
    return mockSearch(query)
  }

  let response: Response
  try {
    response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, {
      signal,
    })
  } catch (error) {
    if (signal.aborted) throw error
    throw new Error('無法連線到後端，請確認 Flask 已啟動（預設 http://127.0.0.1:5000）。', {
      cause: error,
    })
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }
  const data = (await response.json()) as ApiSearchResponse
  return {
    query,
    indexedCount: data.indexed_count,
    results: data.results,
  }
}
