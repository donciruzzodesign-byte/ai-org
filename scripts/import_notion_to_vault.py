"""Notionの3か所をObsidian保管庫へ取り込み、重複・類似をグループにまとめる。

取り込み元(読むだけ。Notionは変更しない):
  1. コンテンツ生成物 DB (NOTION_DATABASE_ID)      → 06_Notion/コンテンツ生成物/
  2. コンテンツ生成物保管ファイル (ページ+子ページ)   → 06_Notion/保管ファイル/
  3. ソムリエ学習ノート DB (上級者向け)             → 08_ソムリエ学習ノート/  (別グループ。州メモとはリンクで連携)
類似・重複は 07_類似・重複/ に「グループ」メモを作り、各メモからリンクする。
取り込んだメモは先頭の自動生成マーカーで見分け、実行のたびに作り直す(手書きのメモは触らない)。

使い方: python3 scripts/import_notion_to_vault.py [--vault パス] [--save-cache f.json | --load-cache f.json]
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

DEFAULT_VAULT = os.path.expanduser("~/Documents/ワイン台帳")
STUDY_DB_ID = "c152f173e72c410ab84bac264e58275d"
ARCHIVE_PAGE_ID = "3601eebc398281deab5dc68a5747a19b"
MARK = "<!-- 自動生成: scripts/import_notion_to_vault.py(Notionから取り込み)。手で書き足す場合は本文の下に -->"
FOLDERS = {"生成物": "06_Notion/コンテンツ生成物", "保管": "06_Notion/保管ファイル", "学習": "08_ソムリエ学習ノート"}
GROUP_DIR = "07_類似・重複"
SIMILAR_THRESHOLD = 0.6
MIN_BODY = 200


# ---------- Notion → Markdown(通信なし。テスト対象) ----------

def rich_text_md(rich: list) -> str:
    out = []
    for t in rich or []:
        s = t.get("plain_text", "")
        if not s:
            continue
        a = t.get("annotations", {})
        if a.get("code"):
            s = f"`{s}`"
        if a.get("bold"):
            s = f"**{s}**"
        if a.get("italic"):
            s = f"*{s}*"
        if a.get("strikethrough"):
            s = f"~~{s}~~"
        if t.get("href") and t.get("type") == "text":
            s = f"[{s}]({t['href']})"
        out.append(s)
    return "".join(out)


def blocks_md(blocks: list, depth: int = 0) -> str:
    """children を取得済みのブロック一覧をMarkdownにする。本文中の `[[` は、リンクにならないよう無効化する。"""
    return _blocks_md(blocks, depth).replace("[[", "\\[\\[")


def _blocks_md(blocks: list, depth: int = 0) -> str:
    lines = []
    ind = "  " * depth
    n = 0
    for b in blocks:
        t = b["type"]
        d = b.get(t, {})
        n = n + 1 if t == "numbered_list_item" else 0
        text = rich_text_md(d.get("rich_text"))
        kids = _blocks_md(b.get("children", []), depth + 1) if b.get("children") and t not in ("table", "column_list", "column") else ""
        if t == "paragraph":
            lines.append(f"{ind}{text}")
        elif t in ("heading_1", "heading_2", "heading_3"):
            lines.append(f"{'#' * (int(t[-1]) + 1)} {text}")
        elif t == "bulleted_list_item":
            lines.append(f"{ind}- {text}")
        elif t == "numbered_list_item":
            lines.append(f"{ind}{n}. {text}")
        elif t == "to_do":
            lines.append(f"{ind}- [{'x' if d.get('checked') else ' '}] {text}")
        elif t == "toggle":
            lines.append(f"{ind}- ▶ {text}")
        elif t == "quote":
            lines.append(f"> {text}")
        elif t == "callout":
            lines.append(f"> {(d.get('icon') or {}).get('emoji', '💡')} {text}")
        elif t == "code":
            lines.append(f"```{d.get('language', '')}\n{''.join(x.get('plain_text', '') for x in d.get('rich_text', []))}\n```")
        elif t == "divider":
            lines.append("---")
        elif t == "table":
            rows = [[rich_text_md(c) for c in r["table_row"]["cells"]] for r in b.get("children", []) if r["type"] == "table_row"]
            if rows:
                w = max(len(r) for r in rows)
                rows = [r + [""] * (w - len(r)) for r in rows]
                lines.append("| " + " | ".join(rows[0]) + " |")
                lines.append("|" + "---|" * w)
                lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        elif t in ("column_list", "column"):
            lines.append(_blocks_md(b.get("children", []), depth))
        elif t in ("image", "file", "pdf", "video", "bookmark", "embed", "link_preview"):
            url = d.get("url") or (d.get("file") or d.get("external") or {}).get("url", "")
            cap = rich_text_md(d.get("caption")) or t
            lines.append(f"[{cap}]({url})" if url else f"({t})")
        elif t == "child_page":
            lines.append(f"- 📄 {d.get('title', '')}")
        elif t == "equation":
            lines.append(f"$${d.get('expression', '')}$$")
        if kids:
            lines.append(kids)
    return "\n".join(lines)


def prop_value(p: dict):
    t = p["type"]
    v = p.get(t)
    if t in ("select", "status"):
        return (v or {}).get("name")
    if t == "multi_select":
        return [x["name"] for x in v or []]
    if t == "date":
        return (v or {}).get("start")
    if t in ("rich_text",):
        return "".join(x.get("plain_text", "") for x in v or []) or None
    if t in ("number", "checkbox", "url", "email", "phone_number"):
        return v
    return None


def page_title(page: dict) -> str:
    for p in page["properties"].values():
        if p["type"] == "title":
            return "".join(t.get("plain_text", "") for t in p["title"]).strip()
    return ""


def jst_date(iso: str) -> str:
    return (datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=9)).strftime("%Y-%m-%d")


def safe_name(title: str, limit: int = 80) -> str:
    s = re.sub(r'[#^\[\]|\\/:*?"<>]', "・", title).strip(" .・")
    return (s[:limit].rstrip(" .・")) or "無題"


# ---------- 重複・類似 ----------

def shingles(text: str, n: int = 5) -> set:
    t = re.sub(r"\s+", "", re.sub(r"[#>*`\-\[\]()|]", "", text))[:4000]
    return {hash(t[i:i + n]) for i in range(max(len(t) - n + 1, 0))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _union_find(ids):
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    return parent, find


def bigrams(text: str) -> set:
    t = re.sub(r"\s+", "", text)
    return {t[i:i + 2] for i in range(len(t) - 1)}


_DATE_TAIL = re.compile(r"\s*[\(（]?\s*-?\s*\d{4}-\d{2}-\d{2}[^)）]*[\)）]?\s*$")


def task_label(title: str) -> str:
    """「月曜：テーマ決定 (2026-06-04)」→「月曜：テーマ決定」。"""
    return _DATE_TAIL.sub("", title).strip()


def cluster(items: list, threshold: float = SIMILAR_THRESHOLD, title_threshold: float = None) -> list:
    """items: [{"id","body", "title"?, "created"?, "theme"?}]。次のどれかで結ばれたものをグループ(2件以上)にして返す。
    ・同じタスク名で同じ日に作られた(再生成による重複)
    ・本文がほぼ同じ/似ている(Jaccard>=threshold)
    ・テーマが似ている(2文字ずつのJaccard>=0.6)
    ・title_threshold を渡したときは、題名が似ている(同一題名は除く。学習ノート用)
    各グループは (メンバーIDの一覧, "重複" か "類似") の組。"""
    ids = [i["id"] for i in items]
    parent, find = _union_find(ids)
    sh = {i["id"]: shingles(i["body"]) for i in items if len(i["body"]) >= MIN_BODY}
    md5 = {i["id"]: hashlib.md5(i["body"].encode()).hexdigest() for i in items if len(i["body"]) >= MIN_BODY}
    theme = {i["id"]: bigrams(i["theme"]) for i in items if i.get("theme")}
    title = {i["id"]: bigrams(task_label(i.get("title", ""))) for i in items}
    strict = {}  # 同名・同日
    for i in items:
        if i.get("title") and i.get("created"):
            strict.setdefault((task_label(i["title"]), i["created"]), []).append(i["id"])
    pairs = []
    for g in strict.values():
        pairs += [(g[0], x) for x in g[1:]]
    for a_ in range(len(items)):
        for b_ in range(a_ + 1, len(items)):
            x, y = items[a_]["id"], items[b_]["id"]
            if x in md5 and y in md5 and (md5[x] == md5[y] or jaccard(sh[x], sh[y]) >= threshold):
                pairs.append((x, y))
            elif x in theme and y in theme and jaccard(theme[x], theme[y]) >= 0.6:
                pairs.append((x, y))
            elif title_threshold and task_label(items[a_]["title"]) != task_label(items[b_]["title"]) \
                    and jaccard(title[x], title[y]) >= title_threshold:
                pairs.append((x, y))
    for x, y in pairs:
        parent[find(x)] = find(y)
    groups = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)
    by_id = {i["id"]: i for i in items}
    out = []
    for g in groups.values():
        if len(g) < 2:
            continue
        keys = {(task_label(by_id[x].get("title", "")), by_id[x].get("created")) for x in g}
        same_task_day = len(keys) == 1 and bool(by_id[g[0]].get("title"))
        same_body = len({md5.get(x) for x in g}) == 1 and bool(md5.get(g[0]))
        out.append((g, "重複" if same_task_day or same_body else "類似"))
    return out


# ---------- ノートの作成 ----------

def regions_in(text: str) -> list:
    from scripts.build_wine_graph import _states_in
    return _states_in(text, None)


def build_notes(pages: list, vault: str) -> dict:
    """pages: [{"id","source","title","created","edited","props","body"}] をvaultへ書く。"""
    names, notes = {}, []
    used = set()
    for p in sorted(pages, key=lambda x: (x["source"], x["created"], x["title"])):
        base = safe_name(p["title"] if p["source"] == "学習" else f"{p['created']} {p['title']}")
        name = base
        if (p["source"], name) in used:
            name = f"{base} ({p['id'][-4:]})"
        used.add((p["source"], name))
        names[p["id"]] = name
        notes.append((p, name))

    # 取り込み先を一度きれいにする(マーカー付きのメモだけ)
    for sub in [*FOLDERS.values(), GROUP_DIR]:
        d = os.path.join(vault, sub)
        for root, _, files in os.walk(d):
            for f in files:
                path = os.path.join(root, f)
                if f.endswith(".md") and MARK in open(path, encoding="utf-8").read():
                    os.remove(path)

    groups_of = {}
    for scope, sources in (("生成物系", ("生成物", "保管")), ("学習ノート", ("学習",))):
        items = [{"id": p["id"], "body": p["body"], "title": p["title"], "created": p["created"],
                  "theme": p["props"].get("テーマ", "")} for p, _ in notes if p["source"] in sources]
        found = cluster(items, title_threshold=0.7 if scope == "学習ノート" else None)
        for k, (g, kind) in enumerate(sorted(found, key=lambda x: names[x[0][0]]), 1):
            members = [(p, nm) for p, nm in notes if p["id"] in g]
            first = min((p for p, _ in members), key=lambda p: p["created"])
            gname = safe_name(f"{kind}グループ・{scope}{k:02d}・{task_label(first['title'])}", 90)
            for pid in g:
                groups_of[pid] = gname
            lines = [MARK, "", f"#{kind}グループ", "", f"# {gname}", "", f"- 範囲: {scope}", f"- 種類: {kind}"
                     + ("（同じ題名・同じ日に作られたもの＝再生成の重複）" if kind == "重複" else "（本文・テーマ・題名が似ているもの）"),
                     f"- 件数: {len(g)}", ""]
            lines += [f"- [[{nm}]]（{p['created']}）" for p, nm in sorted(members, key=lambda m: m[0]["created"])]
            path = os.path.join(vault, GROUP_DIR, gname + ".md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    hubs = {"学習": "ソムリエ学習ノート", "生成物": "コンテンツ生成物", "保管": "コンテンツ生成物保管ファイル"}
    for p, name in notes:
        tags = {"学習": ["上級者", "学習ノート"], "生成物": ["生成物"], "保管": ["保管ファイル"]}[p["source"]]
        if "（失敗）" in p["title"]:
            tags.append("失敗")
        if p["id"] in groups_of:
            tags.append("類似・重複")
        fm = ["---", f"notion_id: {p['id']}", f"source: {json.dumps(hubs[p['source']], ensure_ascii=False)}",
              f"created: {p['created']}", f"tags: [{', '.join(tags)}]"]
        for k, v in p["props"].items():
            if v not in (None, "", []):
                fm.append(f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}")
        fm += ["---", MARK]
        states = regions_in(p["title"] + " " + " ".join(str(v) for v in p["props"].values() if isinstance(v, str)))
        links = [f"- 親: [[{hubs[p['source']]}]]"] + [f"- 州: [[{s}]]" for s in states]
        if p["id"] in groups_of:
            links.append(f"- 類似・重複: [[{groups_of[p['id']]}]]")
        body = "\n".join(fm) + f"\n\n# {p['title']}\n\n" + "\n".join(links) + "\n\n" + p["body"].strip() + "\n"
        path = os.path.join(vault, FOLDERS[p["source"]], name + ".md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(body)

    for hub, folder in (("ソムリエ学習ノート", "学習"), ("コンテンツ生成物", "生成物"), ("コンテンツ生成物保管ファイル", "保管")):
        lines = [MARK, "", "#ハブ" + ("/上級者" if folder == "学習" else ""), "", f"# {hub}", "",
                 f"- 件数: {sum(1 for p, _ in notes if p['source'] == folder)}"]
        if folder == "学習":
            lines.append("- 上級者向け。グラフでは別グループとして表示し、州のメモとだけリンクでつなぐ")
        path = os.path.join(vault, FOLDERS[folder].rsplit("/", 1)[0] if folder != "学習" else FOLDERS[folder], hub + ".md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return {"学習": sum(p["source"] == "学習" for p, _ in notes), "生成物": sum(p["source"] == "生成物" for p, _ in notes),
            "保管": sum(p["source"] == "保管" for p, _ in notes), "類似グループ": len(set(groups_of.values()))}


# ---------- Notionから取得(通信あり) ----------

class Notion:
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
        from tools import _notion_headers
        self.h = _notion_headers(os.environ["NOTION_API_KEY"])

    def req(self, method: str, path: str, **kw):
        import requests
        for attempt in range(6):
            time.sleep(0.34)
            r = requests.request(method, "https://api.notion.com/v1/" + path, headers=self.h, timeout=60, **kw)
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2)))
                continue
            if r.status_code >= 500:
                time.sleep(2)
                continue
            return r.json()
        raise RuntimeError(f"Notion API が応答しません: {path}")

    def query_all(self, db_id: str) -> list:
        rows, cur = [], None
        while True:
            r = self.req("POST", f"databases/{db_id}/query", json={"page_size": 100, **({"start_cursor": cur} if cur else {})})
            rows += r["results"]
            if not r.get("has_more"):
                return rows
            cur = r["next_cursor"]

    def blocks(self, block_id: str, child_pages: list = None) -> list:
        out, cur = [], None
        while True:
            r = self.req("GET", f"blocks/{block_id}/children?page_size=100" + (f"&start_cursor={cur}" if cur else ""))
            for b in r.get("results", []):
                if b["type"] == "child_page" and child_pages is not None:
                    child_pages.append((b["id"], b["child_page"]["title"]))
                if b.get("has_children") and b["type"] not in ("child_page", "child_database"):
                    b["children"] = self.blocks(b["id"], child_pages)
                out.append(b)
            if not r.get("has_more"):
                return out
            cur = r["next_cursor"]


def _record(page: dict, source: str, body: str) -> dict:
    props = {}
    for k, v in page["properties"].items():
        if v["type"] != "title":
            val = prop_value(v)
            if val not in (None, "", []):
                props[k] = val
    return {"id": page["id"], "source": source, "title": page_title(page), "created": jst_date(page["created_time"]),
            "edited": jst_date(page["last_edited_time"]), "props": props, "body": body}


def fetch_all(log=print) -> list:
    n = Notion()
    pages = []
    for source, db in (("生成物", os.environ["NOTION_DATABASE_ID"]), ("学習", STUDY_DB_ID)):
        rows = n.query_all(db)
        log(f"{source}: {len(rows)}件を読み込み中")
        for i, row in enumerate(rows, 1):
            pages.append(_record(row, source, blocks_md(n.blocks(row["id"]))))
            if i % 25 == 0:
                log(f"  {source} {i}/{len(rows)}")
    # 保管ファイル: ページ直下から子ページを再帰でたどる
    queue, seen = [(ARCHIVE_PAGE_ID, "")], set()
    while queue:
        pid, _ = queue.pop(0)
        kids = []
        blocks = n.blocks(pid, kids)
        if pid != ARCHIVE_PAGE_ID:
            page = n.req("GET", f"pages/{pid}")
            pages.append(_record(page, "保管", blocks_md(blocks)))
            if len([p for p in pages if p["source"] == "保管"]) % 25 == 0:
                log(f"  保管 {len([p for p in pages if p['source'] == '保管'])}件")
        for cid, ctitle in kids:
            if cid not in seen:
                seen.add(cid)
                queue.append((cid, ctitle))
    log(f"保管: {len([p for p in pages if p['source'] == '保管'])}件")
    return pages


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--save-cache")
    ap.add_argument("--load-cache")
    a = ap.parse_args()
    if a.load_cache:
        pages = json.load(open(a.load_cache, encoding="utf-8"))
    else:
        pages = fetch_all(lambda m: print(m, flush=True))
        if a.save_cache:
            json.dump(pages, open(a.save_cache, "w", encoding="utf-8"), ensure_ascii=False)
    print(build_notes(pages, a.vault))
