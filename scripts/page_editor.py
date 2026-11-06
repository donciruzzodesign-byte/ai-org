"""LPページ(docs/day1 など)を、ブラウザ上で直接編集して保存するローカル編集ツール。

文章はクリックして直接書き換え、写真の枠はクリック(またはドラッグ)で差し替える。
自分のPCの 127.0.0.1 だけで動き、外からは開けない。保存すると index.html と assets/ を更新する。
「公開する」ボタンは、そのフォルダだけをコミットして push する(GitHub Pages に反映される)。

使い方: python3 scripts/page_editor.py [--dir docs/day1] [--port 8766]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BACKUP_DIR = os.path.join(ROOT, "output", "page_backups")  # output/ はGit管理外
KEEP_BACKUPS = 30
MAX_UPLOAD = 15 * 1024 * 1024
SAFE_IMG = re.compile(r"^[A-Za-z0-9_\-]+\.jpg$")
SITE_RE = re.compile(r"window\.SITE\s*=\s*\{.*?\};", re.S)
FILL_SCRIPT_RE = re.compile(r"<script>\s*\(function \(\) \{\s*var c = window\.SITE.*?</script>", re.S)

EDITOR_JS = r"""
(function () {
  var INLINE = {BR:1, SPAN:1, B:1, STRONG:1, EM:1, I:1, A:1, SMALL:1};
  var SKIP = {SCRIPT:1, STYLE:1, FIGURE:1, IMG:1, HEAD:1, NOSCRIPT:1};
  function isLeaf(el) {
    if (SKIP[el.tagName] || el.closest("[data-editor]")) return false;
    var hasText = false;
    for (var n = el.firstChild; n; n = n.nextSibling) {
      if (n.nodeType === 1 && !INLINE[n.tagName]) return false;
      if (n.nodeType === 3 && n.textContent.trim()) hasText = true;
      if (n.nodeType === 1 && n.textContent.trim()) hasText = true;
    }
    return hasText;
  }
  document.querySelectorAll("body *").forEach(function (el) {
    if (isLeaf(el) && !el.closest("figure:not(.photo)") ) el.setAttribute("contenteditable", "true");
  });
  document.querySelectorAll("figcaption").forEach(function (el) { el.setAttribute("contenteditable", "true"); });
  document.querySelectorAll("[data-fill], .file, #form-link, #form-todo").forEach(function (el) {
    el.setAttribute("contenteditable", "false");
  });
  document.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function (e) { e.preventDefault(); }); });

  var css = document.createElement("style"); css.setAttribute("data-editor", "1");
  css.textContent =
    "[contenteditable=true]:hover{outline:1px dashed #C9A84C;outline-offset:2px}" +
    "[contenteditable=true]:focus{outline:2px solid #C9A84C;outline-offset:2px;background:rgba(201,168,76,.12)}" +
    "figure.photo{cursor:pointer;position:relative}figure.photo:hover{outline:3px solid #C9A84C}" +
    "figure.photo.drag{outline:3px dashed #C0182F}" +
    "#ed-bar{position:fixed;top:0;left:0;right:0;z-index:99999;background:#222;color:#fff;font:14px/1.4 sans-serif;padding:8px 12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}" +
    "#ed-bar button,#ed-bar a{background:#C9A84C;color:#222;border:0;border-radius:4px;padding:6px 12px;font-size:14px;cursor:pointer;text-decoration:none}" +
    "#ed-bar .pub{background:#C0182F;color:#fff}#ed-bar input{padding:5px;border-radius:4px;border:0;width:170px}" +
    "#ed-bar label{display:flex;gap:4px;align-items:center}#ed-msg{margin-left:auto}body{padding-top:96px!important}";
  document.head.appendChild(css);

  var s = window.SITE || {};
  var bar = document.createElement("div"); bar.id = "ed-bar"; bar.setAttribute("data-editor", "1");
  bar.innerHTML =
    '<button id="ed-save">保存</button><button id="ed-red">選択部分を赤/戻す</button>' +
    '<a href="/index.html" target="_blank">見え方を確認</a>' +
    '<label>配信時刻<input id="ed-time" placeholder="例 20時"></label>' +
    '<label>フォームURL<input id="ed-form" placeholder="https://forms.gle/..."></label>' +
    '<button class="pub" id="ed-pub">公開する</button><span id="ed-msg">文章はクリックして直接書き換え、写真の枠はクリックで差し替え</span>';
  document.body.appendChild(bar);
  document.getElementById("ed-time").value = s.deliveryTime || "";
  document.getElementById("ed-form").value = s.formUrl || "";
  var msg = function (t, bad) { var m = document.getElementById("ed-msg"); m.textContent = t; m.style.color = bad ? "#FF9AA6" : "#fff"; };

  document.getElementById("ed-red").onclick = function () {
    var sel = window.getSelection(); if (!sel.rangeCount || sel.isCollapsed) { msg("赤にしたい文字を選んでから押してください", 1); return; }
    var r = sel.getRangeAt(0), node = r.commonAncestorContainer; node = node.nodeType === 1 ? node : node.parentNode;
    var red = node.closest("span.red");
    if (red) { while (red.firstChild) red.parentNode.insertBefore(red.firstChild, red); red.remove(); return; }
    var sp = document.createElement("span"); sp.className = "red";
    try { r.surroundContents(sp); } catch (e) { msg("複数の段落にまたがる選択は赤にできません。1段落ずつ選んでください", 1); }
  };

  function resizeToJpeg(file, cb) {
    var url = URL.createObjectURL(file), img = new Image();
    img.onload = function () {
      var w = img.naturalWidth, h = img.naturalHeight, k = Math.min(1, 1600 / Math.max(w, h));
      var c = document.createElement("canvas"); c.width = Math.round(w * k); c.height = Math.round(h * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      c.toBlob(function (b) { URL.revokeObjectURL(url); cb(b); }, "image/jpeg", 0.85);
    };
    img.onerror = function () { msg("この画像は読み込めませんでした(JPEG/PNG/WebPをお試しください)", 1); };
    img.src = url;
  }
  function setPhoto(fig, file) {
    var im = fig.querySelector("img"), name = (im.getAttribute("src") || "").split("/").pop().split("?")[0].replace(/\.[^.]*$/, "") + ".jpg";
    resizeToJpeg(file, function (blob) {
      fetch("/upload?name=" + encodeURIComponent(name), {method: "POST", body: blob}).then(function (r) { return r.json(); }).then(function (j) {
        if (!j.ok) { msg("写真の保存に失敗: " + j.error, 1); return; }
        im.setAttribute("src", "assets/" + name); im.src = "assets/" + name + "?t=" + Date.now();
        fig.classList.remove("empty");
        var cap = fig.querySelector("figcaption"); if (cap) { cap.textContent = ""; }
        msg("写真を入れました(" + name + ")。「保存」で確定します");
      });
    });
  }
  document.querySelectorAll("figure.photo").forEach(function (fig) {
    var inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*"; inp.style.display = "none"; inp.setAttribute("data-editor", "1");
    fig.appendChild(inp);
    inp.onchange = function () { if (inp.files[0]) setPhoto(fig, inp.files[0]); };
    fig.addEventListener("click", function (e) { if (e.target.closest("figcaption")) return; inp.click(); });
    fig.addEventListener("dragover", function (e) { e.preventDefault(); fig.classList.add("drag"); });
    fig.addEventListener("dragleave", function () { fig.classList.remove("drag"); });
    fig.addEventListener("drop", function (e) { e.preventDefault(); fig.classList.remove("drag"); if (e.dataTransfer.files[0]) setPhoto(fig, e.dataTransfer.files[0]); });
  });

  var ORIGINAL = Array.prototype.slice.call(document.body.children);  // ブラウザ拡張が後から足す要素を保存しないため
  function cleanHtml() {
    var body = document.body.cloneNode(true);
    Array.prototype.slice.call(body.children).forEach(function (n, i) {
      if (ORIGINAL.indexOf(document.body.children[i]) < 0) n.remove();
    });
    body.querySelectorAll("[data-editor], script, style, link").forEach(function (n) { n.remove(); });
    body.querySelectorAll("[contenteditable]").forEach(function (n) { n.removeAttribute("contenteditable"); });
    body.querySelectorAll("img").forEach(function (im) { im.setAttribute("src", (im.getAttribute("src") || "").split("?")[0]); });
    body.querySelectorAll("figure.photo").forEach(function (f) { f.classList.remove("drag"); if (f.querySelector("img[src]") && !f.dataset.empty) f.classList.remove("empty"); });
    body.removeAttribute("style");
    return body.innerHTML;
  }
  function post(url, body) {
    return fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)}).then(function (r) { return r.json(); });
  }
  function save() {
    return post("/save", {body: cleanHtml(), deliveryTime: document.getElementById("ed-time").value.trim(), formUrl: document.getElementById("ed-form").value.trim()})
      .then(function (j) { msg(j.ok ? "保存しました " + new Date().toLocaleTimeString() : "保存に失敗: " + j.error, !j.ok); return j.ok; });
  }
  document.getElementById("ed-save").onclick = save;
  document.addEventListener("keydown", function (e) { if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); save(); } });
  document.getElementById("ed-pub").onclick = function () {
    if (!confirm("保存した内容をインターネットに公開します(GitHubに送信)。よろしいですか？")) return;
    save().then(function (ok) { if (ok) post("/publish", {}).then(function (j) { msg(j.ok ? j.message : "公開に失敗: " + j.error, !j.ok); }); });
  };
})();
"""


def prepare_edit_page(html: str) -> str:
    """元のHTMLから、画面を書き換える通常スクリプトを外し、編集ツールを差し込む。"""
    html = FILL_SCRIPT_RE.sub("", html)
    return html.replace("</body>", f'<script data-editor="1">{EDITOR_JS}</script>\n</body>')


def apply_site(html: str, form_url: str, delivery_time: str) -> str:
    block = "window.SITE = {\n  formUrl: %s,\n  deliveryTime: %s\n};" % (
        json.dumps(form_url, ensure_ascii=False), json.dumps(delivery_time, ensure_ascii=False))
    if not SITE_RE.search(html):
        raise ValueError("window.SITE の設定欄が見つかりません")
    return SITE_RE.sub(lambda m: block, html, count=1)


BODY_RE = re.compile(r"^(<body[^>]*>)(.*)(</body>)", re.S | re.M)  # 行頭のタグだけ(コメント内の文字は除く)


def splice_body(original: str, body_html: str) -> str:
    """元のHTMLの <head> などはそのままに、<body> の中身だけを差し替える。
    編集画面では外してある表示用スクリプト(window.SITE を画面に反映する部分)は元どおり戻す。"""
    m = BODY_RE.search(original)
    if not m:
        raise ValueError("元のページに <body> が見つかりません")
    fill = FILL_SCRIPT_RE.search(m.group(2))
    inner = "\n" + body_html.strip() + "\n" + (fill.group(0) + "\n" if fill else "")
    return original[:m.start(2)] + inner + original[m.end(2):]


def save_page(page_dir: str, body_html: str, form_url: str, delivery_time: str) -> str:
    if not body_html.strip():
        raise ValueError("本文が空です")
    path = os.path.join(page_dir, "index.html")
    original = open(path, encoding="utf-8").read()
    html = apply_site(splice_body(original, body_html), form_url, delivery_time)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    with open(os.path.join(BACKUP_DIR, f"{os.path.basename(page_dir)}-{stamp}.html"), "w", encoding="utf-8") as f:
        f.write(original)
    for old in sorted(os.listdir(BACKUP_DIR))[:-KEEP_BACKUPS]:
        os.remove(os.path.join(BACKUP_DIR, old))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def save_image(page_dir: str, name: str, data: bytes) -> str:
    if not SAFE_IMG.match(name):
        raise ValueError("ファイル名が不正です")
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("JPEG画像ではありません")
    if len(data) > MAX_UPLOAD:
        raise ValueError("画像が大きすぎます")
    assets = os.path.join(page_dir, "assets")
    os.makedirs(assets, exist_ok=True)
    path = os.path.join(assets, name)
    with open(path, "wb") as f:
        f.write(data)
    return path


def publish(page_dir: str) -> str:
    """そのフォルダだけをコミットして push する。"""
    repo = subprocess.run(["git", "-C", page_dir, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    rel = os.path.relpath(page_dir, repo)
    run = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    run("add", "--", rel)
    if run("diff", "--cached", "--quiet", "--", rel).returncode == 0:
        return "変更がないため、公開内容は変わりません"
    c = run("commit", "-m", f"docs: {rel} のページを更新", "--", rel)
    if c.returncode != 0:
        raise RuntimeError(c.stderr.strip() or c.stdout.strip())
    p = run("push")
    if p.returncode != 0:
        raise RuntimeError("pushに失敗: " + p.stderr.strip())
    return "公開しました。反映まで1〜2分かかることがあります"


def make_handler(page_dir: str):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body: bytes, ctype="text/html; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def _local_only(self) -> bool:
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("127.0.0.1", "localhost")

        def do_GET(self):
            if not self._local_only():
                return self._send(403, b"forbidden")
            path = unquote(urlparse(self.path).path)
            if path == "/":
                html = open(os.path.join(page_dir, "index.html"), encoding="utf-8").read()
                return self._send(200, prepare_edit_page(html).encode())
            full = os.path.realpath(os.path.join(page_dir, path.lstrip("/")))
            if not full.startswith(os.path.realpath(page_dir) + os.sep) or not os.path.isfile(full):
                return self._send(404, b"not found")
            ctype = {".html": "text/html; charset=utf-8", ".jpg": "image/jpeg", ".png": "image/png", ".css": "text/css", ".js": "text/javascript"}.get(os.path.splitext(full)[1], "application/octet-stream")
            self._send(200, open(full, "rb").read(), ctype)

        def do_POST(self):
            if not self._local_only():
                return self._send(403, b"forbidden")
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n)
            u = urlparse(self.path)
            try:
                if u.path == "/save":
                    d = json.loads(body)
                    save_page(page_dir, d["body"], d.get("formUrl", ""), d.get("deliveryTime", ""))
                    return self._json({"ok": True})
                if u.path == "/upload":
                    name = unquote(u.query.split("name=", 1)[1]) if "name=" in u.query else ""
                    save_image(page_dir, name, body)
                    return self._json({"ok": True})
                if u.path == "/publish":
                    return self._json({"ok": True, "message": publish(page_dir)})
                return self._json({"ok": False, "error": "unknown"}, 404)
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 400)

    return H


def serve(page_dir: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(page_dir))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "docs", "day1"))
    ap.add_argument("--port", type=int, default=8766)
    a = ap.parse_args()
    d = os.path.abspath(a.dir)
    srv = serve(d, a.port)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"編集画面: {url}  (終了: Ctrl+C)")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
