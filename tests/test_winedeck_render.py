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


def _render_diag_decks(tmp_path):
    outs = {}
    for name in ("diag_taste_type", "diag_activation_level"):
        spec = os.path.join(WINEDECK_DIR, "decks", name, f"{name}.json")
        outdir = tmp_path / name
        result = subprocess.run(
            [sys.executable, RENDER_PATH, spec, "--outdir", str(outdir), "--svg-only"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "[warn]" not in result.stderr, result.stderr
        outs[name] = outdir / "svg"
    return outs


def test_diagnosis_decks_render_without_length_warnings(tmp_path):
    outs = _render_diag_decks(tmp_path)
    for svg_dir in outs.values():
        assert len(os.listdir(svg_dir)) == 11


def test_quiz_and_result_slides_draw_markers_and_next_step(tmp_path):
    outs = _render_diag_decks(tmp_path)
    quiz = (outs["diag_taste_type"] / "diag_taste_type_02.svg").read_text(encoding="utf-8")
    assert "<polygon" in quiz and "<rect" in quiz  # triangle/diamond/square markers
    result = (outs["diag_activation_level"] / "diag_activation_level_07.svg").read_text(encoding="utf-8")
    assert "Lv.1" in result and "NEXT STEP" in result
