import type { SearchResult } from './api.ts'

type ResultListProps = {
  results: SearchResult[]
}

// 連結只允許 http / https，其他協定（javascript: 等）一律不產生連結。
function toSafeHref(rawUrl: string): string | null {
  try {
    const url = new URL(rawUrl)
    return url.protocol === 'http:' || url.protocol === 'https:'
      ? url.href
      : null
  } catch {
    return null
  }
}

export default function ResultList({ results }: ResultListProps) {
  return (
    <ol className="result-list">
      {results.map((result, index) => {
        const href = toSafeHref(result.url)
        return (
          <li key={result.url} className="result-item">
            <div className="result-head">
              <span className="result-rank">{index + 1}</span>
              <h2 className="result-title">
                {href ? (
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    {result.title}
                  </a>
                ) : (
                  result.title
                )}
              </h2>
              <span className="result-score">
                分數 {result.score.toFixed(4)}
              </span>
            </div>
            <p className="result-url">{result.url}</p>
            {/* 標題與摘要都以純文字渲染，不使用 dangerouslySetInnerHTML */}
            <p className="result-snippet">{result.snippet}</p>
          </li>
        )
      })}
    </ol>
  )
}
