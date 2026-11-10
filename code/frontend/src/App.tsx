import { useRef, useState } from 'react'
import './App.css'
import { searchDocuments } from './api.ts'
import type { SearchResponse } from './api.ts'
import ResultList from './ResultList.tsx'
import SearchBar from './SearchBar.tsx'

type SearchState =
  | { status: 'idle' }
  | { status: 'empty' }
  | { status: 'loading' }
  | { status: 'done'; response: SearchResponse }
  | { status: 'error'; message: string }

export default function App() {
  const [state, setState] = useState<SearchState>({ status: 'idle' })
  const [indexedCount, setIndexedCount] = useState<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  async function handleSearch(rawQuery: string) {
    abortRef.current?.abort()
    const query = rawQuery.trim()
    if (!query) {
      setState({ status: 'empty' })
      return
    }

    const controller = new AbortController()
    abortRef.current = controller
    setState({ status: 'loading' })

    try {
      const response = await searchDocuments(query, controller.signal)
      if (controller.signal.aborted) return
      // 已索引頁數來自搜尋回應的 indexed_count（後端沒有獨立的 stats 端點）
      setIndexedCount(response.indexedCount)
      setState({ status: 'done', response })
    } catch (error) {
      if (controller.signal.aborted) return
      const message = error instanceof Error ? error.message : '未知錯誤'
      setState({ status: 'error', message })
    }
  }

  return (
    <main className="app">
      <header className="app-header">
        <h1>Web Search Engine</h1>
        <p className="app-subtitle">
          {indexedCount === null
            ? '小型主題式搜尋引擎'
            : `已索引 ${indexedCount} 個網頁`}
        </p>
      </header>

      <SearchBar loading={state.status === 'loading'} onSearch={handleSearch} />

      <section className="app-content" aria-live="polite">
        {state.status === 'idle' && (
          <p className="message">輸入關鍵字開始搜尋。</p>
        )}
        {state.status === 'empty' && (
          <p className="message message-warning">請輸入至少一個關鍵字。</p>
        )}
        {state.status === 'loading' && <p className="message">搜尋中…</p>}
        {state.status === 'error' && (
          <p className="message message-error">
            搜尋失敗：{state.message}
          </p>
        )}
        {state.status === 'done' && (
          <>
            <p className="summary">
              「{state.response.query}」共 {state.response.results.length} 筆結果
              （從 {state.response.indexedCount} 個已索引網頁中）
            </p>
            {state.response.results.length === 0 ? (
              <p className="message">
                找不到符合「{state.response.query}」的結果，請換個關鍵字再試試。
              </p>
            ) : (
              <ResultList results={state.response.results} />
            )}
          </>
        )}
      </section>
    </main>
  )
}
