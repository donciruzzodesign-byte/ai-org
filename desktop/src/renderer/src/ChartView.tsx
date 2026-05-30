import React, { useEffect, useRef, useState } from 'react'
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  ColorType,
  IChartApi,
} from 'lightweight-charts'
import { getStock, getFundamentals } from './api'
import type { Candle, Fundamentals } from './types'

const PERIODS = ['1mo', '3mo', '6mo', '1y', '2y', '5y'] as const
type Period = typeof PERIODS[number]

interface Props {
  initialTicker?: string
}

export default function ChartView({ initialTicker = '' }: Props): JSX.Element {
  const [ticker, setTicker] = useState(initialTicker)
  const [inputTicker, setInputTicker] = useState(initialTicker)
  const [period, setPeriod] = useState<Period>('1y')
  const [fundamentals, setFundamentals] = useState<Fundamentals | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const mainRef = useRef<HTMLDivElement>(null)
  const rsiRef = useRef<HTMLDivElement>(null)
  const macdRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const rsiChartRef = useRef<IChartApi | null>(null)
  const macdChartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!ticker || !mainRef.current || !rsiRef.current || !macdRef.current) return

    let isMounted = true

    const chart = createChart(mainRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0d1117' }, textColor: '#e6edf3' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      width: mainRef.current.offsetWidth,
      height: 400,
    })
    chartRef.current = chart

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#3fb950', downColor: '#f85149',
      borderUpColor: '#3fb950', borderDownColor: '#f85149',
      wickUpColor: '#3fb950', wickDownColor: '#f85149',
    })
    const ma5Series = chart.addSeries(LineSeries, { color: '#58a6ff', lineWidth: 1 })
    const ma25Series = chart.addSeries(LineSeries, { color: '#f0883e', lineWidth: 1 })
    const ma75Series = chart.addSeries(LineSeries, { color: '#bc8cff', lineWidth: 1 })
    const bbUpperSeries = chart.addSeries(LineSeries, { color: '#8b949e', lineWidth: 1, lineStyle: 2 })
    const bbMidSeries = chart.addSeries(LineSeries, { color: '#8b949e', lineWidth: 1, lineStyle: 1 })
    const bbLowerSeries = chart.addSeries(LineSeries, { color: '#8b949e', lineWidth: 1, lineStyle: 2 })

    const rsiChart = createChart(rsiRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0d1117' }, textColor: '#e6edf3' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      width: rsiRef.current.offsetWidth,
      height: 120,
    })
    rsiChartRef.current = rsiChart
    const rsiSeries = rsiChart.addSeries(LineSeries, { color: '#79c0ff', lineWidth: 1 })

    const macdChart = createChart(macdRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0d1117' }, textColor: '#e6edf3' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      width: macdRef.current.offsetWidth,
      height: 120,
    })
    macdChartRef.current = macdChart
    const macdLineSeries = macdChart.addSeries(LineSeries, { color: '#79c0ff', lineWidth: 1 })
    const macdSignalSeries = macdChart.addSeries(LineSeries, { color: '#f0883e', lineWidth: 1 })
    const macdHistSeries = macdChart.addSeries(HistogramSeries, {
      color: '#3fb950',
    })

    setLoading(true)
    setError(null)

    getStock(ticker, period)
      .then(({ data }) => {
        if (!isMounted) return
        const candles = data as Candle[]
        candleSeries.setData(candles.map((c) => ({
          time: c.time as any, open: c.open, high: c.high, low: c.low, close: c.close,
        })))
        ma5Series.setData(candles.filter((c) => c.ma5 != null).map((c) => ({ time: c.time as any, value: c.ma5! })))
        ma25Series.setData(candles.filter((c) => c.ma25 != null).map((c) => ({ time: c.time as any, value: c.ma25! })))
        ma75Series.setData(candles.filter((c) => c.ma75 != null).map((c) => ({ time: c.time as any, value: c.ma75! })))
        bbUpperSeries.setData(candles.filter((c) => c.bb_upper != null).map((c) => ({ time: c.time as any, value: c.bb_upper! })))
        bbMidSeries.setData(candles.filter((c) => c.bb_mid != null).map((c) => ({ time: c.time as any, value: c.bb_mid! })))
        bbLowerSeries.setData(candles.filter((c) => c.bb_lower != null).map((c) => ({ time: c.time as any, value: c.bb_lower! })))
        rsiSeries.setData(candles.filter((c) => c.rsi != null).map((c) => ({ time: c.time as any, value: c.rsi! })))
        macdLineSeries.setData(candles.filter((c) => c.macd != null).map((c) => ({ time: c.time as any, value: c.macd! })))
        macdSignalSeries.setData(candles.filter((c) => c.macd_signal != null).map((c) => ({ time: c.time as any, value: c.macd_signal! })))
        macdHistSeries.setData(candles.filter((c) => c.macd_hist != null).map((c) => ({
          time: c.time as any, value: c.macd_hist!,
          color: (c.macd_hist ?? 0) >= 0 ? '#3fb950' : '#f85149',
        })))
        chart.timeScale().fitContent()
        rsiChart.timeScale().fitContent()
        macdChart.timeScale().fitContent()
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))

    getFundamentals(ticker)
      .then(setFundamentals)
      .catch(() => setFundamentals(null))

    return () => {
      isMounted = false
      chart.remove()
      rsiChart.remove()
      macdChart.remove()
    }
  }, [ticker, period])

  const handleSearch = (): void => {
    if (inputTicker.trim()) setTicker(inputTicker.trim().toUpperCase())
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <input
          value={inputTicker}
          onChange={(e) => setInputTicker(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="銘柄コード (例: AAPL, 7203.T)"
          style={{ flex: 1, minWidth: 200, padding: '6px 10px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: 6 }}
        />
        <button onClick={handleSearch} style={{ padding: '6px 16px', background: '#1f6feb', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer' }}>
          検索
        </button>
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            style={{ padding: '6px 10px', background: period === p ? '#1f6feb' : '#21262d', border: 'none', color: '#e6edf3', borderRadius: 6, cursor: 'pointer' }}
          >
            {p}
          </button>
        ))}
      </div>
      {fundamentals && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 12, fontSize: 13, color: '#8b949e' }}>
          <span>PER: {fundamentals.per?.toFixed(1) ?? 'N/A'}</span>
          <span>PBR: {fundamentals.pbr?.toFixed(2) ?? 'N/A'}</span>
          <span>自己資本比率: {fundamentals.equity_ratio != null ? `${fundamentals.equity_ratio}%` : 'N/A'}</span>
        </div>
      )}
      {loading && <p style={{ color: '#8b949e' }}>読み込み中...</p>}
      {error && (
        <p style={{ color: '#f85149' }}>
          エラー: {error}
          <button onClick={handleSearch} style={{ marginLeft: 8, padding: '2px 8px', background: '#21262d', border: 'none', color: '#e6edf3', borderRadius: 4, cursor: 'pointer' }}>
            リトライ
          </button>
        </p>
      )}
      <div ref={mainRef} style={{ width: '100%' }} />
      <div style={{ color: '#8b949e', fontSize: 12, margin: '4px 0' }}>RSI (14)</div>
      <div ref={rsiRef} style={{ width: '100%' }} />
      <div style={{ color: '#8b949e', fontSize: 12, margin: '4px 0' }}>MACD (12,26,9)</div>
      <div ref={macdRef} style={{ width: '100%' }} />
    </div>
  )
}
