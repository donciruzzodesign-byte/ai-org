import React, { useEffect, useState } from 'react'
import { getWatchlist, addToWatchlist, removeFromWatchlist, getSettings, putSettings } from './api'

interface Props {
  onSelectTicker: (ticker: string) => void
}

export default function WatchlistView({ onSelectTicker }: Props): JSX.Element {
  const [tickers, setTickers] = useState<string[]>([])
  const [newTicker, setNewTicker] = useState('')
  const [alertInterval, setAlertInterval] = useState('15')
  const [error, setError] = useState<string | null>(null)

  const loadWatchlist = (): void => {
    getWatchlist()
      .then(({ tickers }) => setTickers(tickers))
      .catch((e: Error) => setError(e.message))
  }

  useEffect(() => {
    loadWatchlist()
    getSettings().then(({ alert_interval_minutes }) => setAlertInterval(alert_interval_minutes))
  }, [])

  const handleAdd = (): void => {
    if (!newTicker.trim()) return
    addToWatchlist(newTicker.trim())
      .then(() => { setNewTicker(''); loadWatchlist() })
      .catch((e: Error) => setError(e.message))
  }

  const handleRemove = (ticker: string): void => {
    removeFromWatchlist(ticker).then(loadWatchlist)
  }

  const handleSaveInterval = (): void => {
    putSettings(alertInterval).catch((e: Error) => setError(e.message))
  }

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 12, fontSize: 16 }}>ウォッチリスト</h2>
      {error && <p style={{ color: '#f85149', marginBottom: 8 }}>{error}</p>}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder="銘柄追加 (例: 6758.T)"
          style={{ flex: 1, padding: '6px 10px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
        />
        <button onClick={handleAdd} style={{ padding: '6px 16px', background: '#1f6feb', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer' }}>
          追加
        </button>
      </div>
      {tickers.length === 0 ? (
        <p style={{ color: '#8b949e' }}>銘柄がありません。上のフォームから追加してください。</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', fontSize: 13 }}>
              <th style={{ textAlign: 'left', padding: '6px 8px' }}>銘柄</th>
              <th style={{ textAlign: 'right', padding: '6px 8px' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {tickers.map((t) => (
              <tr key={t} style={{ borderBottom: '1px solid #21262d' }}>
                <td
                  onClick={() => onSelectTicker(t)}
                  style={{ padding: '8px', cursor: 'pointer', color: '#58a6ff' }}
                >
                  {t}
                </td>
                <td style={{ padding: '8px', textAlign: 'right' }}>
                  <button
                    onClick={() => handleRemove(t)}
                    style={{ padding: '2px 8px', background: '#da3633', border: 'none', color: '#fff', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
                  >
                    削除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div style={{ marginTop: 24, borderTop: '1px solid #30363d', paddingTop: 16 }}>
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>アラート設定</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label style={{ fontSize: 13, color: '#8b949e' }}>チェック間隔:</label>
          <input
            type="number"
            value={alertInterval}
            onChange={(e) => setAlertInterval(e.target.value)}
            min="1"
            style={{ width: 60, padding: '4px 8px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
          />
          <span style={{ fontSize: 13, color: '#8b949e' }}>分</span>
          <button onClick={handleSaveInterval} style={{ padding: '4px 12px', background: '#238636', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
            保存
          </button>
        </div>
      </div>
    </div>
  )
}
