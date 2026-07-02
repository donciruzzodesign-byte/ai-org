import os
import subprocess
import sys

WINEDECK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "winedeck"
)
RENDER_PATH = os.path.join(WINEDECK_DIR, "render.py")
DECK_EXAMPLE_PATH = os.path.join(WINEDECK_DIR, "deck.example.json")


def test_cli_default_outdir_lands_under_desktop_weekly_carousel(tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    env = {**os.environ, "HOME": str(fake_home)}
    result = subprocess.run(
        [sys.executable, RENDER_PATH, DECK_EXAMPLE_PATH, "--date", "2026-07-06", "--svg-only"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    svg_dir = fake_home / "Desktop" / "CUBOCCI_STUDIO" / "weekly" / "2026-07-06-wine" / "carousel" / "svg"
    files = sorted(os.listdir(svg_dir))
    assert files == ["barolo_01.svg", "barolo_02.svg", "barolo_03.svg", "barolo_04.svg"]


def test_cli_explicit_outdir_overrides_default(tmp_path):
    outdir = tmp_path / "custom"
    result = subprocess.run(
        [sys.executable, RENDER_PATH, DECK_EXAMPLE_PATH, "--outdir", str(outdir), "--svg-only"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert os.path.exists(os.path.join(str(outdir), "svg", "barolo_01.svg"))
