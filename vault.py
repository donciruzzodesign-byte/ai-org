"""ワイン台帳(Obsidian保管庫)の読み書きと類似判定。

保管庫は WINE_VAULT_PATH で指定する。未設定・存在しない・書き込み不可のときは
例外を出さず「台帳なし」として扱う(従来動作を壊さない)。
"""
import os
import re
from typing import Optional

SEP = "｜"
MIN_COLS = 5  # B-roll.md が5列、他は6列
_STOP = {"a", "the", "of", "in", "on", "with", "and"}


def vault_path() -> Optional[str]:
    p = os.environ.get("WINE_VAULT_PATH", "").strip()
    return p if p and os.path.isdir(p) else None


def _ledger(vault: str, ledger_file: str) -> str:
    return os.path.join(vault, "01_台帳", ledger_file)


def append_row(vault: Optional[str], ledger_file: str, cols: list) -> bool:
    if not vault:
        return False
    clean = [re.sub(r"[｜\r\n]+", " ", str(c)).strip() for c in cols]
    path = _ledger(vault, ledger_file)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = SEP.join(clean) + "\n"
        if not os.path.exists(path):
            text = f"# {ledger_file}\n" + text
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
        return True
    except OSError:
        return False


def read_rows(vault: Optional[str], ledger_file: str, limit: int = 10) -> list:
    if not vault:
        return []
    try:
        with open(_ledger(vault, ledger_file), encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    rows = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        cols = [c.strip() for c in line.split(SEP)]
        if len(cols) >= MIN_COLS:
            rows.append(cols)
    return rows[-limit:] if limit > 0 else []


def slug_words(video_url: str) -> set:
    m = re.search(r"/video/([^/?#]+)", video_url or "")
    if not m:
        return set()
    return {
        w for w in m.group(1).lower().split("-")
        if w and not w.isdigit() and w not in _STOP
    }


def is_similar(words: set, recent: list, threshold: float = 0.5) -> bool:
    if not words:
        return False
    for other in recent:
        if not other:
            continue
        union = words | other
        if union and len(words & other) / len(union) >= threshold:
            return True
    return False


def recent_broll_words(vault: Optional[str], limit: int = 30) -> list:
    return [set(r[2].lower().split()) for r in read_rows(vault, "B-roll.md", limit)]


def ledger_summary(vault: Optional[str], limit: int = 10) -> str:
    rows = read_rows(vault, "投稿テーマ.md", limit)
    return "\n".join(f"・{r[0]}（{r[2]}）" for r in rows)
