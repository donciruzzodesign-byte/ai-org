from typing import List, Dict, Any
from screener.data import fetch_ohlcv, fetch_fundamentals, fetch_vix
from screener.indicators import add_indicators, is_golden_cross, is_bb_breakout

_OPS = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}


def evaluate_condition(condition: Dict[str, Any], ticker: str) -> bool:
    field = condition["field"]
    op = condition["op"]
    threshold = condition["value"]

    df = fetch_ohlcv(ticker)
    df = add_indicators(df)
    latest = df.iloc[-1]

    if field == "golden_cross":
        return is_golden_cross(df)

    if field in ("per", "pbr", "equity_ratio"):
        fund = fetch_fundamentals(ticker)
        actual = fund.get(field)
        if actual is None:
            return False
    elif field == "vix":
        actual = fetch_vix()
    elif field == "rsi":
        actual = float(latest["rsi"])
    elif field == "bb_lower":
        return is_bb_breakout(df)["lower"]
    elif field == "bb_upper":
        return is_bb_breakout(df)["upper"]
    else:
        return False

    fn = _OPS.get(op)
    return fn(actual, threshold) if fn else False


def run_screen(tickers: List[str], conditions: List[Dict], logic: str = "AND") -> List[str]:
    results = []
    for ticker in tickers:
        try:
            evals = [evaluate_condition(c, ticker) for c in conditions]
            passed = all(evals) if logic == "AND" else any(evals)
            if passed:
                results.append(ticker)
        except Exception:
            continue
    return results
