export interface Candle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  ma5: number | null
  ma25: number | null
  ma75: number | null
  bb_upper: number | null
  bb_mid: number | null
  bb_lower: number | null
  rsi: number | null
  macd: number | null
  macd_signal: number | null
  macd_hist: number | null
}

export interface StockResponse {
  ticker: string
  data: Candle[]
}

export interface Fundamentals {
  per: number | null
  pbr: number | null
  equity_ratio: number | null
  market_cap: number | null
}

export type ConditionField =
  | 'rsi' | 'per' | 'pbr' | 'equity_ratio'
  | 'vix' | 'bb_lower' | 'bb_upper' | 'golden_cross'

export type ConditionOp = '<' | '>' | '<=' | '>=' | '=='

export interface Condition {
  field: ConditionField
  op: ConditionOp
  value: number
}

export interface AlertMessage {
  type: 'alert'
  ticker: string
  direction: 'upper' | 'lower'
}
