import type { Condition, Fundamentals, StockResponse } from './types'

const BASE = 'http://localhost:8765'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

export const getStock = (ticker: string, period = '1y'): Promise<StockResponse> =>
  req(`/stock/${encodeURIComponent(ticker)}?period=${period}`)

export const getFundamentals = (ticker: string): Promise<Fundamentals> =>
  req(`/fundamentals/${encodeURIComponent(ticker)}`)

export const getVix = (): Promise<{ vix: number }> => req('/vix')

export const getWatchlist = (): Promise<{ tickers: string[] }> => req('/watchlist')

export const addToWatchlist = (ticker: string, name = ''): Promise<{ ok: boolean }> =>
  req('/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, name }),
  })

export const removeFromWatchlist = (ticker: string): Promise<{ ok: boolean }> =>
  req(`/watchlist/${encodeURIComponent(ticker)}`, { method: 'DELETE' })

export const runScreen = (
  conditions: Condition[],
  logic: 'AND' | 'OR' = 'AND',
  tickers?: string[]
): Promise<{ matched: string[] }> =>
  req('/screen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conditions, logic, tickers }),
  })

export const getSettings = (): Promise<{ alert_interval_minutes: string }> => req('/settings')

export const putSettings = (alert_interval_minutes: string): Promise<{ ok: boolean }> =>
  req('/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alert_interval_minutes }),
  })

export function connectAlerts(onAlert: (ticker: string, direction: string) => void): WebSocket {
  const ws = new WebSocket('ws://localhost:8765/ws/alerts')
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data as string)
      if (data.type === 'alert') {
        onAlert(data.ticker as string, data.direction as string)
      }
    } catch {
      // ignore malformed messages
    }
  }
  return ws
}
