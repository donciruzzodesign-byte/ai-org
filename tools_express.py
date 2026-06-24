import os

DESKTOP_DIR = os.path.expanduser("~/Desktop/CUBOCCI_STUDIO")
TEMPLATES_DIR = os.path.join(DESKTOP_DIR, "templates")
WEEKLY_BASE_DIR = os.path.join(DESKTOP_DIR, "weekly")

PRIMARY = "#6B1A2A"
ACCENT = "#C9A84C"
BACKGROUND = "#F5F0E8"
TEXT = "#2C2C2C"
BRAND = "CUBOCCI STUDIO"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def get_weekly_dir(date_str: str, theme: str, base_dir: str = WEEKLY_BASE_DIR) -> str:
    path = os.path.join(base_dir, f"{date_str}-{theme}")
    _ensure_dir(path)
    return path
