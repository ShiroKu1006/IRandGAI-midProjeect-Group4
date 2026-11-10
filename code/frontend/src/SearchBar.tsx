import { useState } from 'react'

type SearchBarProps = {
  loading: boolean
  onSearch: (query: string) => void
}

export default function SearchBar({ loading, onSearch }: SearchBarProps) {
  const [value, setValue] = useState('')

  return (
    <form
      className="search-bar"
      role="search"
      onSubmit={(event) => {
        event.preventDefault()
        onSearch(value)
      }}
    >
      <input
        type="search"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="輸入關鍵字，例如 inverted index"
        aria-label="搜尋關鍵字"
        autoFocus
      />
      <button type="submit" disabled={loading}>
        {loading ? '搜尋中…' : '搜尋'}
      </button>
    </form>
  )
}
