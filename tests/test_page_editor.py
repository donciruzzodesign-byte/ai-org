import json
import os
import subprocess
import sys
import threading
import urllib.request

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import scripts.page_editor as pe

PAGE = """<!DOCTYPE html><html><head><!-- 本文は <body> の中 --><script>
window.SITE = {
  formUrl: "",
  deliveryTime: ""
};
</script></head>
<body>
<p>本文</p>
<script>
(function () {
  var c = window.SITE || {};
})();
</script>
</body></html>
"""


@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.setattr(pe, "BACKUP_DIR", str(tmp_path / "bk"))
    d = tmp_path / "day1"
    d.mkdir()
    (d / "index.html").write_text(PAGE, encoding="utf-8")
    return d


def test_edit_page_drops_fill_script_and_adds_editor():
    html = pe.prepare_edit_page(PAGE)
    assert "var c = window.SITE" not in html
    assert 'data-editor="1"' in html


def test_apply_site_writes_values_and_escapes():
    out = pe.apply_site(PAGE, 'https://x/"y', "20時")
    assert 'formUrl: "https://x/\\"y"' in out and 'deliveryTime: "20時"' in out


def test_save_replaces_only_body_keeps_head_and_fill_script(page):
    pe.save_page(str(page), "<p>直した</p>", "https://forms.gle/a", "20時")
    saved = (page / "index.html").read_text(encoding="utf-8")
    assert "直した" in saved and "<p>本文</p>" not in saved and "var c = window.SITE" in saved
    assert 'formUrl: "https://forms.gle/a"' in saved and saved.count("<head>") == 1
    assert len(os.listdir(pe.BACKUP_DIR)) == 1


def test_save_rejects_empty_body(page):
    with pytest.raises(ValueError):
        pe.save_page(str(page), "  ", "", "")
    assert "本文" in (page / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["../x.jpg", "a/b.jpg", "x.png", "x.jpg.html", ""])
def test_image_name_rejected(page, name):
    with pytest.raises(ValueError):
        pe.save_image(str(page), name, b"\xff\xd8abc")


def test_image_saved_and_non_jpeg_rejected(page):
    pe.save_image(str(page), "hero.jpg", b"\xff\xd8abc")
    assert (page / "assets" / "hero.jpg").read_bytes() == b"\xff\xd8abc"
    with pytest.raises(ValueError):
        pe.save_image(str(page), "hero.jpg", b"<html>")


def test_server_serves_editor_blocks_foreign_host_and_traversal(page):
    srv = pe.serve(str(page), 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        assert 'data-editor="1"' in urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/", headers={"Host": "evil.example"})
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == 403
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/..%2f..%2fetc/passwd")
        assert e.value.code == 404
    finally:
        srv.shutdown()


def test_publish_commits_only_page_dir(tmp_path, monkeypatch):
    for k in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{k}_NAME", "t")
        monkeypatch.setenv(f"GIT_{k}_EMAIL", "t@t")
    remote, repo = tmp_path / "r.git", tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True)
    g("remote", "add", "origin", str(remote))
    (repo / "README").write_text("r")
    g("add", "README")
    g("commit", "-q", "-m", "init")
    g("push", "-q", "-u", "origin", "main")
    page = repo / "docs" / "day1"
    page.mkdir(parents=True)
    (page / "index.html").write_text("a")
    (repo / "other.txt").write_text("secret")
    assert "公開しました" in pe.publish(str(page))
    assert g("show", "--name-only", "--format=", "HEAD").stdout.split() == ["docs/day1/index.html"]
    assert "変更がない" in pe.publish(str(page))
