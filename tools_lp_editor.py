import http.server
import json
import os
import subprocess
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_PATH = os.path.join(ROOT, "docs", "content.json")
DEPLOY_SH = os.path.join(ROOT, "docs", "deploy.sh")


def _load_env():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


class LPEditorHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[editor] {fmt % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path == "/":
            self._serve_html(_editor_html())
        elif path == "/content":
            try:
                with open(CONTENT_PATH, encoding="utf-8") as f:
                    self._serve_html(f.read(), content_type="application/json; charset=utf-8")
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
        elif path == "/pexels":
            self._serve_pexels(query)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/save":
            self._handle_save()
        elif self.path == "/deploy":
            self._handle_deploy()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_html(self, body_str, content_type="text/html; charset=utf-8"):
        body = body_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_pexels(self, query):
        q = query.get("q", [""])[0]
        media_type = query.get("type", ["photo"])[0]
        api_key = os.environ.get("PEXELS_API_KEY", "")
        if not api_key:
            self._json_response({"error": "PEXELS_API_KEY が未設定です"}, 400)
            return
        if not q:
            self._json_response({"error": "検索キーワードを入力してください"}, 400)
            return
        try:
            if media_type == "video":
                url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(q)}&per_page=12"
            else:
                url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(q)}&per_page=12"
            req = urllib.request.Request(url, headers={
                "Authorization": api_key,
                "User-Agent": "Mozilla/5.0 (compatible; LP-Editor/1.0)",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._json_response(data)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_save(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            content = json.loads(raw.decode("utf-8"))
            tmp_path = CONTENT_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            from tools_lp import write_lp
            write_lp(content)
            os.replace(tmp_path, CONTENT_PATH)
            self._json_response({"status": "ok", "message": "保存完了"})
        except Exception as e:
            # clean up temp file if it exists
            try:
                os.remove(CONTENT_PATH + ".tmp")
            except OSError:
                pass
            self._json_response({"status": "error", "message": str(e)}, 500)

    def _handle_deploy(self):
        try:
            result = subprocess.run(
                ["bash", DEPLOY_SH],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                self._json_response({
                    "status": "ok",
                    "url": "https://donciruzzodesign-byte.github.io/ai-org/",
                    "output": result.stdout,
                })
            else:
                self._json_response(
                    {"status": "error", "message": result.stderr or result.stdout}, 500
                )
        except Exception as e:
            self._json_response({"status": "error", "message": str(e)}, 500)


def _editor_html():
    return """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LP エディタ</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Noto Sans JP',sans-serif;background:#f0ece4;color:#333}
    #topbar{position:sticky;top:0;z-index:100;background:#6B1A2A;color:#F5F0E8;
      padding:12px 20px;display:flex;align-items:center;gap:12px;box-shadow:0 2px 6px rgba(0,0,0,.3)}
    #topbar h1{font-size:18px;flex:1}
    .btn{padding:8px 20px;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:bold}
    .btn-save{background:#C9A84C;color:#6B1A2A}
    .btn-deploy{background:#2a6b2a;color:#fff}
    #status{font-size:13px;min-width:140px}
    .card{background:#fff;margin:16px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.1);overflow:hidden}
    .card-header{background:#6B1A2A;color:#F5F0E8;padding:12px 16px;cursor:pointer;
      display:flex;justify-content:space-between;font-weight:bold;user-select:none}
    .card-body{padding:16px;display:none}
    .card-body.open{display:block}
    label{display:block;font-size:12px;color:#888;margin:12px 0 4px}
    label:first-child{margin-top:0}
    input[type=text],textarea{width:100%;padding:8px 10px;border:1px solid #ddd;
      border-radius:4px;font-size:14px;font-family:inherit}
    textarea{min-height:80px;resize:vertical}
    .row{display:flex;gap:8px;align-items:center}
    .row input{flex:1}
    .btn-px{padding:8px 12px;background:#05A081;color:#fff;border:none;
      border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap}
    .list-item{display:flex;gap:8px;margin-bottom:8px}
    .list-item input{flex:1}
    .btn-del{background:#c44;color:#fff;border:none;border-radius:4px;padding:6px 10px;cursor:pointer}
    .btn-add{background:#C9A84C;color:#fff;border:none;border-radius:4px;
      padding:8px 16px;cursor:pointer;margin-top:8px;font-size:13px}
    fieldset{border:1px solid #e0d8cc;border-radius:4px;padding:12px;margin-bottom:12px}
    legend{font-weight:bold;color:#6B1A2A;font-size:13px;padding:0 4px}
    #modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;overflow:auto;padding:40px 20px}
    #modal.open{display:block}
    #modal-inner{background:#fff;max-width:800px;margin:0 auto;border-radius:8px;overflow:hidden}
    #modal-head{background:#6B1A2A;color:#F5F0E8;padding:12px 16px;display:flex;gap:8px;align-items:center}
    #modal-head input{flex:1;padding:8px;border:none;border-radius:4px}
    #modal-head .search-btn{padding:8px 16px;background:#C9A84C;border:none;border-radius:4px;cursor:pointer;font-weight:bold}
    #modal-close{background:none;border:none;color:#F5F0E8;font-size:22px;cursor:pointer;margin-left:auto;line-height:1}
    #modal-grid{padding:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;max-height:60vh;overflow:auto}
    .res{cursor:pointer;border-radius:4px;overflow:hidden;border:2px solid transparent}
    .res:hover{border-color:#C9A84C}
    .res img{width:100%;height:110px;object-fit:cover;display:block}
    .res-url{font-size:10px;color:#666;padding:4px;word-break:break-all}
  </style>
</head>
<body>
<div id="topbar">
  <h1>LP エディタ</h1>
  <button class="btn btn-save" onclick="saveContent()">💾 保存</button>
  <button class="btn btn-deploy" onclick="deployContent()">🚀 デプロイ</button>
  <span id="status"></span>
</div>
<div id="editor"></div>

<div id="modal">
  <div id="modal-inner">
    <div id="modal-head">
      <input id="px-q" type="text" placeholder="Pexels キーワード（英語推奨）..."
             onkeydown="if(event.key==='Enter')searchPx()">
      <button class="search-btn" onclick="searchPx()">🔍 検索</button>
      <button id="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div id="modal-grid"></div>
  </div>
</div>

<script>
let C={};
let _px_target=null, _px_type='photo';

async function init(){
  const r=await fetch('/content');
  C=await r.json();
  render();
}

function status(msg,ok=true){
  const el=document.getElementById('status');
  el.textContent=msg;
  el.style.color=ok?'#C9A84C':'#ff8888';
}

async function saveContent(){
  status('保存中...');
  try{
    const data=collect();
    const r=await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const res=await r.json();
    res.status==='ok'?status('✅ 保存完了'):(status('❌ '+res.message,false),console.error(res));
  }catch(e){status('❌ '+e.message,false);}
}

async function deployContent(){
  status('デプロイ中...');
  try{
    const r=await fetch('/deploy',{method:'POST'});
    const res=await r.json();
    res.status==='ok'?status('✅ デプロイ完了'):status('❌ '+res.message,false);
  }catch(e){status('❌ '+e.message,false);}
}

function collect(){
  const c=JSON.parse(JSON.stringify(C));
  // simple scalar paths
  document.querySelectorAll('[data-p]').forEach(el=>{
    const parts=el.getAttribute('data-p').split('.');
    let o=c;
    for(let i=0;i<parts.length-1;i++){
      const k=isNaN(parts[i])?parts[i]:+parts[i];
      if(o[k]===undefined) o[k]=isNaN(parts[i+1])?{}:[];
      o=o[k];
    }
    const last=isNaN(parts[parts.length-1])?parts[parts.length-1]:+parts[parts.length-1];
    o[last]=el.value;
  });
  // arrays rebuilt from list containers
  ['worries','ideals','line_steps'].forEach(k=>{
    const el=document.querySelector(`[data-list="${k}"]`);
    if(el) c[k]=[...el.querySelectorAll('input')].map(i=>i.value);
  });
  const giftEl=document.querySelector('[data-list="gift.items"]');
  if(giftEl) c.gift.items=[...giftEl.querySelectorAll('input')].map(i=>i.value);
  c.qa=[...document.querySelectorAll('.qa-item')].map(el=>({
    q:el.querySelector('[data-qa="q"]').value,
    a:el.querySelector('[data-qa="a"]').value,
  }));
  return c;
}

function openPx(inputId,type='photo'){
  _px_target=document.getElementById(inputId);
  _px_type=type;
  document.getElementById('modal').classList.add('open');
  document.getElementById('px-q').focus();
}
function closeModal(){
  document.getElementById('modal').classList.remove('open');
  document.getElementById('modal-grid').innerHTML='';
}
async function searchPx(){
  const q=document.getElementById('px-q').value.trim();
  if(!q)return;
  document.getElementById('modal-grid').innerHTML='<p style="padding:16px">検索中...</p>';
  const r=await fetch(`/pexels?q=${encodeURIComponent(q)}&type=${_px_type}`);
  const data=await r.json();
  const grid=document.getElementById('modal-grid');
  grid.innerHTML='';
  if(data.error){grid.innerHTML=`<p style="padding:16px;color:red">${esc(data.error)}</p>`;return;}
  const items=_px_type==='video'
    ?(data.videos||[]).map(v=>{const f=(v.video_files||[]).find(x=>x.quality==='hd')||(v.video_files||[])[0];return f?{thumb:v.image,url:f.link}:null;}).filter(Boolean)
    :(data.photos||[]).map(p=>({thumb:p.src.medium,url:p.src.large}));
  items.forEach(({thumb,url})=>{
    const d=document.createElement('div');
    d.className='res';
    d.innerHTML=`<img src="${esc(thumb)}" alt=""><div class="res-url">${esc(url)}</div>`;
    d.onclick=()=>{if(_px_target)_px_target.value=url;closeModal();};
    grid.appendChild(d);
  });
  if(!items.length) grid.innerHTML='<p style="padding:16px">結果なし</p>';
}

function esc(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function addItem(key,val=''){
  const c=document.querySelector(`[data-list="${key}"]`);
  const d=document.createElement('div');d.className='list-item';
  d.innerHTML=`<input type="text" value="${esc(val)}"><button class="btn-del" onclick="this.parentElement.remove()">削除</button>`;
  c.appendChild(d);
}
function toggle(h){
  const b=h.nextElementSibling;b.classList.toggle('open');
  h.querySelector('.ico').textContent=b.classList.contains('open')?'▲':'▼';
}

function pxBtn(id,type='photo'){
  return `<button class="btn-px" onclick="openPx('${id}','${type}')">Pexels 🔍</button>`;
}
function mediaInput(label,id,path,type='photo'){
  const val=path.split('.').reduce((o,k)=>o&&o[isNaN(k)?k:+k],C)||'';
  return `<label>${label}</label><div class="row"><input type="text" id="${id}" data-p="${path}" value="${esc(val)}">${pxBtn(id,type)}</div>`;
}
function card(title,bodyHtml){
  return `<div class="card"><div class="card-header" onclick="toggle(this)">${esc(title)}<span class="ico">▼</span></div><div class="card-body">${bodyHtml}</div></div>`;
}
function listItems(key,arr){
  return `<div data-list="${key}">${(arr||[]).map(v=>`<div class="list-item"><input type="text" value="${esc(v)}"><button class="btn-del" onclick="this.parentElement.remove()">削除</button></div>`).join('')}</div><button class="btn-add" onclick="addItem('${key}')">＋ 項目追加</button>`;
}

function render(){
  const c=C;
  let h='';

  h+=card('ヘッダー動画・メインコピー',`
    ${mediaInput('葡萄畑動画 URL（Pexels MP4）','hv','media.header_video','video')}
    <label>キャッチコピー</label><textarea data-p="headline.catch">${esc(c.headline?.catch||'')}</textarea>
    <label>サブテキスト</label><input type="text" data-p="headline.sub" value="${esc(c.headline?.sub||'')}">
    <label>LINE URL</label><input type="text" data-p="meta.line_url" value="${esc(c.meta?.line_url||'')}">
  `);

  h+=card('お悩みセクション',`
    ${mediaInput('セクション写真 URL','img_worries','media.worries.image')}
    <label>お悩みリスト</label>${listItems('worries',c.worries)}
  `);

  h+=card('こうなりたい（理想）',`
    ${mediaInput('セクション写真 URL','img_ideals','media.ideals.image')}
    <label>理想リスト</label>${listItems('ideals',c.ideals)}
  `);

  h+=card('プレゼントセクション',`
    ${mediaInput('セクション写真 URL','img_gift','media.gift.image')}
    <label>タイトル</label><input type="text" data-p="gift.title" value="${esc(c.gift?.title||'')}">
    <label>サブタイトル</label><input type="text" data-p="gift.subtitle" value="${esc(c.gift?.subtitle||'')}">
    <label>説明文</label><textarea data-p="gift.description">${esc(c.gift?.description||'')}</textarea>
    <label>内容リスト</label>${listItems('gift.items',c.gift?.items)}
  `);

  h+=card('LINE 登録セクション',`
    ${mediaInput('セクション写真 URL','img_cta1','media.cta1.image')}
    <label>CTA ボタンテキスト</label><input type="text" data-p="cta_text" value="${esc(c.cta_text||'')}">
    <label>手順リスト</label>${listItems('line_steps',c.line_steps)}
  `);

  h+=card('プロフィールセクション',`
    ${mediaInput('セクション写真 URL','img_profile','media.profile.image')}
    <label>名前</label><input type="text" data-p="profile.name" value="${esc(c.profile?.name||'')}">
    <label>本文</label><textarea data-p="profile.body">${esc(c.profile?.body||'')}</textarea>
  `);

  const storyParts=(c.story||[]).map((p,i)=>`
    <fieldset>
      <legend>パート ${i+1}「${esc(p.title)}」</legend>
      ${mediaInput('写真 URL',`img_st${i}`,`media.story.${i}.image`)}
      <label>タイトル</label><input type="text" data-p="story.${i}.title" value="${esc(p.title||'')}">
      <label>本文</label><textarea data-p="story.${i}.body">${esc(p.body||'')}</textarea>
    </fieldset>`).join('');
  h+=card(`ストーリーセクション（全${(c.story||[]).length}パート）`,storyParts);

  h+=card('なんで無料なの？',`
    ${mediaInput('セクション写真 URL','img_wf','media.why_free.image')}
    <textarea data-p="why_free">${esc(c.why_free||'')}</textarea>
  `);

  h+=card('あなただからなんです！',`
    ${mediaInput('セクション写真 URL','img_wm','media.why_me.image')}
    <textarea data-p="why_me">${esc(c.why_me||'')}</textarea>
  `);

  const qaHtml=(c.qa||[]).map((q,i)=>`
    <div class="qa-item">
      <label>質問 ${i+1}</label><input type="text" data-qa="q" value="${esc(q.q||'')}">
      <label>回答</label><textarea data-qa="a">${esc(q.a||'')}</textarea>
    </div>`).join('');
  h+=card('よくあるご質問',`
    ${mediaInput('セクション写真 URL','img_qa','media.qa.image')}
    ${qaHtml}
  `);

  h+=card('追伸',`
    ${mediaInput('セクション写真 URL','img_ps','media.postscript.image')}
    <textarea data-p="postscript">${esc(c.postscript||'')}</textarea>
  `);

  const fp=c.meta?.font_pair||'elegant';
  const fpOptions=[
    {v:'elegant', l:'エレガント',    d:'Cormorant Garamond × Noto Sans JP'},
    {v:'natural', l:'ナチュラル',    d:'Playfair Display × Noto Sans JP'},
    {v:'classic', l:'クラシック',    d:'EB Garamond × Noto Serif JP'},
    {v:'modern',  l:'モダン',        d:'Montserrat × Noto Sans JP'},
    {v:'wagashi', l:'和モダン',      d:'Zen Old Mincho × Noto Serif JP'},
  ];
  const fpOpts=fpOptions.map(o=>`<option value="${o.v}"${fp===o.v?' selected':''}>${o.l} — ${o.d}</option>`).join('');
  h+=card('フォントペア設定',`
    <label>フォントの組み合わせ</label>
    <select data-p="meta.font_pair">${fpOpts}</select>
    <p style="margin-top:8px;font-size:12px;color:#888">💡 保存・デプロイするとLPのフォントが変わります</p>
  `);

  const fs=c.meta?.font_sizes||{};
  h+=card('フォントサイズ設定',`
    <label>本文サイズ（例: 16px）</label>
    <input type="text" data-p="meta.font_sizes.body" value="${esc(fs.body||'16px')}">
    <label>見出し H1 サイズ（例: clamp(22px, 5vw, 38px) または 32px）</label>
    <input type="text" data-p="meta.font_sizes.h1" value="${esc(fs.h1||'clamp(22px, 5vw, 38px)')}">
    <label>見出し H2 サイズ（例: clamp(20px, 4vw, 28px) または 24px）</label>
    <input type="text" data-p="meta.font_sizes.h2" value="${esc(fs.h2||'clamp(20px, 4vw, 28px)')}">
    <label>見出し H3 サイズ（例: clamp(16px, 3vw, 20px) または 18px）</label>
    <input type="text" data-p="meta.font_sizes.h3" value="${esc(fs.h3||'clamp(16px, 3vw, 20px)')}">
    <p style="margin-top:12px;font-size:12px;color:#888">💡 保存するとLPに即反映されます</p>
  `);

  document.getElementById('editor').innerHTML=h;
}

init();
</script>
</body>
</html>"""


if __name__ == "__main__":
    import webbrowser
    _load_env()
    PORT = 8765
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("localhost", PORT), LPEditorHandler)
    url = f"http://localhost:{PORT}"
    print(f"✅ LP エディタ起動: {url}")
    print("終了するには Ctrl+C を押してください")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✋ サーバーを停止しました")
