import React, { useEffect, useRef, useState } from 'react'
import ChartView from './ChartView'
import ScreenerView from './ScreenerView'
import WatchlistView from './WatchlistView'
import { connectAlerts } from './api'

type Tab = 'chart' | 'screener' | 'watchlist'

interface AlertItem {
  id: number
  ticker: string
  direction: 'upper' | 'lower'
  time: string
}

let alertIdCounter = 0

export default function App(): JSX.Element {
  const [tab, setTab] = useState<Tab>('chart')
  const [chartTicker, setChartTicker] = useState('')
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const connect = (): void => {
      const ws = connectAlerts((ticker, direction) => {
        setAlerts((prev) => [
          {
            id: alertIdCounter++,
            ticker,
            direction: direction as 'upper' | 'lower',
            time: new Date().toLocaleTimeString(),
          },
          ...prev.slice(0, 49),
        ])
        if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
          const label = direction === 'upper' ? 'BB上限突破' : 'BB下限割れ'
          new Notification(`【アラート】${ticker}`, { body: `${label}を検知しました` })
        }
      })
      wsRef.current = ws
    }

    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
      Notification.requestPermission().then(connect)
    } else {
      connect()
    }

    return () => wsRef.current?.close()
  }, [])

  const handleSelectTicker = (ticker: string): void => {
    setChartTicker(ticker)
    setTab('chart')
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 20px',
    background: 'transparent',
    border: 'none',
    borderBottom: active ? '2px solid #58a6ff' : '2px solid transparent',
    color: active ? '#fff' : '#8b949e',
    cursor: 'pointer',
    fontSize: 14,
  })

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header
        style={{
          background: '#161b22',
          borderBottom: '1px solid #30363d',
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
        }}
      >
        <span style={{ fontWeight: 'bold', marginRight: 24, color: '#e6edf3' }}>株スクリーナー</span>
        <button onClick={() => setTab('chart')} style={tabStyle(tab === 'chart')}>
          チャート
        </button>
        <button onClick={() => setTab('screener')} style={tabStyle(tab === 'screener')}>
          スクリーニング
        </button>
        <button onClick={() => setTab('watchlist')} style={tabStyle(tab === 'watchlist')}>
          ウォッチリスト
        </button>
        {alerts.length > 0 && (
          <span style={{ marginLeft: 'auto', fontSize: 12, color: '#f0883e' }}>
            最新: {alerts[0].ticker}{' '}
            {alerts[0].direction === 'upper' ? '↑BB上限' : '↓BB下限'} ({alerts[0].time})
          </span>
        )}
      </header>
      <main style={{ flex: 1, overflow: 'auto' }}>
        {tab === 'chart' && <ChartView initialTicker={chartTicker} />}
        {tab === 'screener' && <ScreenerView onSelectTicker={handleSelectTicker} />}
        {tab === 'watchlist' && <WatchlistView onSelectTicker={handleSelectTicker} />}
      </main>
    </div>
  )
}
