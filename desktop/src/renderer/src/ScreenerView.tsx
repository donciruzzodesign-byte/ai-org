import React, { useState } from 'react'
import { runScreen } from './api'
import type { Condition, ConditionField, ConditionOp } from './types'

const FIELDS: { value: ConditionField; label: string }[] = [
  { value: 'rsi', label: 'RSI' },
  { value: 'per', label: 'PER' },
  { value: 'pbr', label: 'PBR' },
  { value: 'equity_ratio', label: '自己資本比率 (%)' },
  { value: 'vix', label: 'VIX' },
  { value: 'bb_lower', label: 'BB下限を下回る' },
  { value: 'bb_upper', label: 'BB上限を上回る' },
  { value: 'golden_cross', label: 'ゴールデンクロス' },
]

const OPS: ConditionOp[] = ['<', '<=', '>', '>=', '==']

interface Props {
  onSelectTicker: (ticker: string) => void
}

export default function ScreenerView({ onSelectTicker }: Props): JSX.Element {
  const [conditions, setConditions] = useState<Condition[]>([
    { field: 'rsi', op: '<', value: 30 },
  ])
  const [logic, setLogic] = useState<'AND' | 'OR'>('AND')
  const [customTickers, setCustomTickers] = useState('')
  const [matched, setMatched] = useState<string[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addCondition = (): void => {
    setConditions([...conditions, { field: 'rsi', op: '<', value: 30 }])
  }

  const removeCondition = (i: number): void => {
    setConditions(conditions.filter((_, idx) => idx !== i))
  }

  const updateCondition = (i: number, patch: Partial<Condition>): void => {
    setConditions(conditions.map((c, idx) => (idx === i ? { ...c, ...patch } : c)))
  }

  const handleRun = (): void => {
    setLoading(true)
    setError(null)
    const tickers = customTickers.trim()
      ? customTickers.split(',').map((t) => t.trim().toUpperCase()).filter(Boolean)
      : undefined
    runScreen(conditions, logic, tickers)
      .then(({ matched }) => setMatched(matched))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  const isNoValueField = (f: ConditionField): boolean =>
    f === 'golden_cross' || f === 'bb_lower' || f === 'bb_upper'

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 12, fontSize: 16 }}>スクリーニング</h2>
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 13, color: '#8b949e' }}>条件の結合:</span>
        {(['AND', 'OR'] as const).map((l) => (
          <button
            key={l}
            onClick={() => setLogic(l)}
            style={{
              padding: '4px 12px',
              background: logic === l ? '#1f6feb' : '#21262d',
              border: 'none',
              color: '#e6edf3',
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            {l}
          </button>
        ))}
      </div>
      {conditions.map((cond, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            gap: 8,
            marginBottom: 8,
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          <select
            value={cond.field}
            onChange={(e) => updateCondition(i, { field: e.target.value as ConditionField })}
            style={{
              padding: '6px 8px',
              background: '#161b22',
              border: '1px solid #30363d',
              color: '#e6edf3',
              borderRadius: 6,
            }}
          >
            {FIELDS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
          {!isNoValueField(cond.field) && (
            <>
              <select
                value={cond.op}
                onChange={(e) => updateCondition(i, { op: e.target.value as ConditionOp })}
                style={{
                  padding: '6px 8px',
                  background: '#161b22',
                  border: '1px solid #30363d',
                  color: '#e6edf3',
                  borderRadius: 6,
                }}
              >
                {OPS.map((op) => (
                  <option key={op} value={op}>
                    {op}
                  </option>
                ))}
              </select>
              <input
                type="number"
                value={cond.value}
                onChange={(e) => updateCondition(i, { value: Number(e.target.value) })}
                style={{
                  width: 80,
                  padding: '6px 8px',
                  background: '#161b22',
                  border: '1px solid #30363d',
                  color: '#e6edf3',
                  borderRadius: 6,
                }}
              />
            </>
          )}
          <button
            onClick={() => removeCondition(i)}
            style={{
              padding: '4px 8px',
              background: '#da3633',
              border: 'none',
              color: '#fff',
              borderRadius: 4,
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>
      ))}
      <button
        onClick={addCondition}
        style={{
          marginBottom: 16,
          padding: '6px 12px',
          background: '#21262d',
          border: '1px solid #30363d',
          color: '#e6edf3',
          borderRadius: 6,
          cursor: 'pointer',
        }}
      >
        + 条件追加
      </button>
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: '#8b949e', display: 'block', marginBottom: 4 }}>
          対象銘柄 (空欄=ウォッチリスト、カンマ区切りで直接指定可):
        </label>
        <input
          value={customTickers}
          onChange={(e) => setCustomTickers(e.target.value)}
          placeholder="AAPL, MSFT, 7203.T"
          style={{
            width: '100%',
            padding: '6px 10px',
            background: '#161b22',
            border: '1px solid #30363d',
            color: '#e6edf3',
            borderRadius: 6,
          }}
        />
      </div>
      <button
        onClick={handleRun}
        disabled={loading || conditions.length === 0}
        style={{
          padding: '8px 24px',
          background: loading || conditions.length === 0 ? '#6e7681' : '#238636',
          border: 'none',
          color: '#fff',
          borderRadius: 6,
          cursor: loading || conditions.length === 0 ? 'not-allowed' : 'pointer',
          fontSize: 14,
        }}
      >
        {loading ? '実行中...' : 'スクリーニング実行'}
      </button>
      {error && <p style={{ color: '#f85149', marginTop: 12 }}>エラー: {error}</p>}
      {matched !== null && (
        <div style={{ marginTop: 16 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>結果: {matched.length}件</h3>
          {matched.length === 0 ? (
            <p style={{ color: '#8b949e' }}>条件に一致する銘柄はありませんでした。</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', fontSize: 13 }}>
                  <th style={{ textAlign: 'left', padding: '6px 8px' }}>銘柄</th>
                  <th style={{ textAlign: 'right', padding: '6px 8px' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {matched.map((t) => (
                  <tr key={t} style={{ borderBottom: '1px solid #21262d' }}>
                    <td
                      onClick={() => onSelectTicker(t)}
                      style={{ padding: '8px', cursor: 'pointer', color: '#58a6ff' }}
                    >
                      {t}
                    </td>
                    <td style={{ padding: '8px', textAlign: 'right' }}>
                      <button
                        onClick={() => onSelectTicker(t)}
                        style={{
                          padding: '2px 8px',
                          background: '#1f6feb',
                          border: 'none',
                          color: '#fff',
                          borderRadius: 4,
                          cursor: 'pointer',
                          fontSize: 12,
                        }}
                      >
                        チャート表示
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
