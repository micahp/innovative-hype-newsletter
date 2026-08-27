#!/usr/bin/env python3
"""build_pipeline.py — render web/pipeline.html, the desk's pipeline view.

One page, three columns, from whatever runs/latest points at:

  KEYWORDS   corpus seeds (lift-scored by brief.py, the same list the desk
             used) + a per-file corpus inventory
  CLUSTERS   every cluster in input.json with its top terms, source items,
             and its desk verdict (kept / demoted / UNDECIDED as a red flag)
  CARDS      the run's output cards with angle status

Cluster keywords are highlighted inside item titles and card paragraphs so
you can see why a story sits where it sits.

Usage:
  python3 scripts/build_pipeline.py     # writes web/pipeline.html

Static and self-contained: no external requests, no server logic. Re-run
after every desk cycle (or ask the agent to).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
RUNS = os.path.join(REPO, "runs")
OUT = os.path.join(REPO, "web", "pipeline.html")

STOP = set("""
a an the and or but if then than that this these those of in on at to for from by
with without into onto over under about after before between during is are was
were be been being it its it's as not no yes do does did done has have had will
would can could should may might must new news said say says show via more most
just like get got make made take took out up down who what when where why how
all any each her his him she they them their there here he we you your i me my
our us am are isn't aren't don't won't one two first last next big small new old
report reports reported reporting says according after over amid vs
""".split())


def load(path):
    with open(path) as f:
        return json.load(f)


def tokens(text):
    return [w for w in re.findall(r"[a-z][a-z0-9'+-]{2,}", (text or "").lower())
            if w not in STOP and not w.isdigit()]


def cluster_terms(cluster, global_freq, n_clusters, top=8):
    """Terms that carry this cluster: frequent here, rare elsewhere."""
    tf = {}
    items = cluster.get("items") or []
    for it in items:
        for w in set(tokens(it.get("title", "")) + tokens(it.get("body_excerpt", ""))):
            tf[w] = tf.get(w, 0) + 1
    scored = []
    for w, c in tf.items():
        if c < 2 or global_freq.get(w, 0) > max(2, n_clusters * 0.6):
            continue
        scored.append((c * (1.0 + global_freq.get(w, 0)), w))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [w for _, w in scored[:top]]


def corpus_inventory():
    """Per-file counts and flags. Freshness per parsed date, never file tail."""
    import collections
    files = sorted(f for f in os.listdir(os.path.join(REPO, "corpus"))
                   if f.endswith(".jsonl"))
    rows_out = []
    for f in files:
        rows = [json.loads(l) for l in open(os.path.join(REPO, "corpus", f))
                if l.strip()]
        dates = []
        for r in rows:
            # corpus display format carries a middot separator; strip it the
            # same way brief.py's parser does
            d = str(r.get("date") or "").replace("·", "").replace("  ", " ").strip()
            for fmt in ("%b %d, %Y %I:%M %p UTC", "%Y-%m-%dT%H:%M:%S.%fZ"):
                try:
                    dates.append(datetime.strptime(d, fmt))
                    break
                except ValueError:
                    pass
        nitter = sum(1 for r in rows if "nitter." in (r.get("text") or ""))
        empty = sum(1 for r in rows if not (r.get("text") or "").strip())
        rows_out.append({
            "file": f, "rows": len(rows),
            "ids": sum(1 for r in rows if r.get("id")),
            "oldest": min(dates).strftime("%Y-%m-%d") if dates else "-",
            "newest": max(dates).strftime("%Y-%m-%d") if dates else "-",
            "flags": [x for x in (
                ("nitter-footer row" if nitter else ""),
                (f"{empty} empty-text rows" if empty else "")) if x],
        })
    return rows_out


def main():
    latest = os.path.realpath(os.path.join(RUNS, "latest"))
    meta = load(os.path.join(latest, "meta.json"))
    decisions = load(os.path.join(latest, "decisions.json"))
    output = load(os.path.join(latest, "output.json"))
    clusters = load(os.path.join(latest, "input.json"))["clusters"]

    verdict_by_cluster = {d["cluster"]: d for d in decisions.get("decisions", [])}
    undecided = [i for i in range(len(clusters)) if i not in verdict_by_cluster]

    # keywords: global frequency first, then per cluster
    global_freq = {}
    for c in clusters:
        for it in c.get("items") or []:
            for w in set(tokens(it.get("title", "")) + tokens(it.get("body_excerpt", ""))):
                global_freq[w] = global_freq.get(w, 0) + 1

    cluster_views = []
    for i, c in enumerate(clusters):
        terms = cluster_terms(c, global_freq, len(clusters))
        dec = verdict_by_cluster.get(i)
        items = [{
            "title": (it.get("title") or "")[:140],
            "source": it.get("source") or "",
            "link": it.get("link") or "",
            "excerpt": (it.get("body_excerpt") or "")[:150],
        } for it in (c.get("items") or [])]
        cluster_views.append({
            "index": i, "name": c.get("name") or f"cluster {i}",
            "voice_weight": c.get("voice_weight"),
            "terms": terms, "items": items,
            "verdict": (dec or {}).get("verdict", "undecided"),
            "angle": (dec or {}).get("angle"),
            "angle_offered": [
                {"id": k, "score": v}
                for k, v in ((dec or {}).get("angle_offered_scores") or {}).items()],
        })

    # grades: the CARD's quality grade from the desk's --grade pass. The feed
    # rephrases headlines between runs, so match exact text first, then the
    # dedupe's own similarity metric (token overlap >= 0.45 = same story).
    grades, grade_pool = {}, []
    kickers = {}
    try:
        with open(os.path.join(REPO, "web", "brief-feed.json")) as f:
            for c in json.load(f).get("cards", []):
                kickers[c["narrative"]] = c.get("kicker") or ""
                if c.get("quality_grade"):
                    rec = (c["quality_grade"], c.get("quality_note") or "")
                    grades[c["narrative"]] = rec
                    grade_pool.append(
                        (set(tokens(c["narrative"])), rec))
    except Exception:
        grades, grade_pool, kickers = {}, [], {}

    def _grade_for(narrative):
        g = grades.get(narrative)
        if g:
            return g
        toks = set(tokens(narrative))
        if not toks:
            return None
        best, best_rec = 0.0, None
        for ftoks, rec in grade_pool:
            if not ftoks:
                continue
            ov = len(toks & ftoks) / float(min(len(toks), len(ftoks)))
            if ov > best:
                best, best_rec = ov, rec
        return best_rec if best >= 0.45 else None

    card_by_cluster = {c["cluster_index"]: c for c in output.get("cards", [])}
    cards = []
    for idx, cv in enumerate(cluster_views):
        card = card_by_cluster.get(idx)
        if not card:
            continue
        g = _grade_for(card.get("narrative") or "")
        cards.append({
            "cluster_index": idx, "name": cv["name"],
            "verdict": cv["verdict"],
            "narrative": card.get("narrative") or "",
            "kicker": kickers.get(card.get("narrative") or "")
                      or card.get("kicker") or "",
            "paragraph": card.get("paragraph") or "",
            "data_point": card.get("data_point") or "",
            "angle_id": card.get("angle_id") or "none",
            "grade": g[0] if g else "", "grade_note": g[1] if g else "",
            "sources": [cv["items"][j]["link"] for j in card.get("source_ids", [])
                        if j < len(cv["items"])],
        })

    # seeds: the desk's own lift-scored list, imported, not re-derived
    try:
        import brief
        seeds = [{"term": str(s)} for s in brief._live_seeds()]
        seed_error = None
    except Exception as e:  # fail loud on the page, not silent in a chip list
        seeds, seed_error = [], f"seeds unavailable: {e}"

    # perspectives: stance + verbatim exemplars (scripts/build_voice_profile.py)
    try:
        with open(os.path.join(REPO, "voice_profile.json")) as f:
            _vpf = json.load(f)
        perspectives = {
            "built": _vpf.get("built"), "n_posts": _vpf.get("n_posts"),
            "entries": [{"topic": e.get("topic"), "stance": e.get("stance"),
                         "tone": e.get("tone"),
                         "exemplars": (e.get("exemplars") or [])[:2]}
                        for e in _vpf.get("entries", [])],
        }
    except Exception as e:
        perspectives = {"built": None, "entries": [],
                        "error": f"voice profile unavailable: {e}"}

    # grade feedback: the misses the desk prompt is told not to repeat
    misses = []
    try:
        with open(os.path.join(REPO, "runs", "grades.jsonl")) as f:
            latest_g = {}
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("grade") in ("D", "F"):
                    latest_g[r.get("story_key") or r.get("narrative", "")] = r
            misses = sorted(latest_g.values(),
                            key=lambda r: r.get("timestamp", ""))[-8:]
        misses = [{"grade": m.get("grade"), "narrative": (m.get("narrative") or "")[:110],
                   "angle": m.get("angle_id") or "", "note": m.get("note") or ""}
                  for m in misses]
    except Exception:
        misses = []

    data = {
        "run": os.path.basename(latest),
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "meta": {k: meta.get(k) for k in
                 ("timestamp", "code_version", "model", "n_clusters", "pool_key")},
        "totals": {
            "clusters": len(clusters),
            "kept": decisions.get("kept"),
            "demoted": decisions.get("declined_type_gate"),
            "undecided": len(undecided),
            "cards": len(cards),
        },
        "undecided_indexes": undecided,
        "seeds": seeds, "seed_error": seed_error,
        "perspectives": perspectives,
        "misses": misses,
        "corpus": corpus_inventory(),
        "clusters": cluster_views,
        "cards": cards,
    }

    html = PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=True)
                        .replace("</", "<\\/"))
    with open(OUT, "w") as f:
        f.write(html)
    print(f"wrote {OUT} ({len(html)//1024} KB) from run {data['run']}: "
          f"{data['totals']}")


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IH Pipeline</title>
<style>
:root { --bg:#0b0e14; --panel:#12161f; --edge:#232a38; --ink:#dbe2ee; --dim:#7d8799;
        --amber:#f59e0b; --green:#22c55e; --red:#ef4444; --mark:#3d2f07; --markink:#fbbf24; }
@media (prefers-color-scheme: light) {
  :root { --bg:#f4f5f7; --panel:#ffffff; --edge:#d9dde3; --ink:#1c2330; --dim:#5d6675;
          --mark:#fdeeba; --markink:#8a5b00; }
}
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--ink); font:14px/1.45 -apple-system,'Segoe UI',Roboto,sans-serif; padding:16px; overflow-wrap:break-word; }
a { color:var(--amber); text-decoration:none; } a:hover { text-decoration:underline; }
mark { background:var(--mark); color:var(--markink); padding:0 2px; border-radius:3px; }
header { margin-bottom:14px; }
h1 { font-size:19px; letter-spacing:.4px; }
.sub { color:var(--dim); font-size:12.5px; margin-top:3px; }
.chips { margin-top:8px; display:flex; flex-wrap:wrap; gap:6px; }
.chip { background:var(--panel); border:1px solid var(--edge); border-radius:20px; padding:2px 10px; font-size:12px; }
.chip b { font-weight:600; }
.grid { display:grid; grid-template-columns:280px minmax(430px,1fr) minmax(360px,1fr); gap:14px; align-items:start; }
@media (max-width:1250px){ .grid{grid-template-columns:1fr 1fr;} .col-k{grid-column:1/-1;} }
@media (max-width:860px){
  .grid{grid-template-columns:1fr;}
  body{padding:10px;}
  h1{font-size:17px;}
  .col h2{position:static;}
}
.col h2 { font-size:12px; text-transform:uppercase; letter-spacing:1.4px; color:var(--dim); margin-bottom:8px; position:sticky; top:0; background:var(--bg); padding:4px 0; z-index:2; }
.panel { background:var(--panel); border:1px solid var(--edge); border-radius:8px; padding:10px 12px; margin-bottom:10px; }
.seed { display:inline-block; background:var(--bg); border:1px solid var(--edge); border-radius:4px; padding:1px 7px; margin:0 4px 5px 0; font-size:12px; }
table { width:100%; border-collapse:collapse; font-size:12px; }
td, th { text-align:left; padding:3px 6px; border-bottom:1px solid var(--edge); }
th { color:var(--dim); font-weight:500; }
.num { text-align:right; font-variant-numeric:tabular-nums; }
.flag { color:var(--amber); font-size:11px; }
.cluster { border-left:3px solid var(--edge); }
.cluster.kept { border-left-color:var(--green); }
.cluster.demoted_type_gate { border-left-color:var(--amber); }
.cluster.undecided { border-left-color:var(--red); }
.badge { float:right; font-size:10.5px; border-radius:4px; padding:1px 7px; font-weight:600; letter-spacing:.4px; }
.kept .badge { background:rgba(34,197,94,.14); color:var(--green); }
.demoted_type_gate .badge { background:rgba(245,158,11,.14); color:var(--amber); }
.undecided .badge { background:rgba(239,68,68,.14); color:var(--red); }
.cname { font-weight:600; margin-bottom:4px; }
.terms { margin:5px 0 7px; }
.term { color:var(--dim); font-size:11.5px; background:var(--bg); border:1px solid var(--edge); border-radius:3px; padding:0 6px; margin-right:4px; }
.item { margin:7px 0 0; font-size:13px; }
.item .src { color:var(--dim); font-size:11px; }
.item .ex { color:var(--dim); font-size:12px; margin-top:1px; }
.vw { color:var(--dim); font-size:11px; }
.card .narr { font-weight:600; font-size:14px; margin-bottom:4px; }
.card .para { font-size:13px; margin-bottom:6px; }
.card .dp { font-family:ui-monospace,Menlo,monospace; font-size:12px; border:1px dashed var(--edge); border-radius:6px; padding:5px 8px; margin-bottom:6px; }
.tag { display:inline-block; font-size:10.5px; border-radius:4px; padding:1px 7px; margin-right:5px; font-weight:600; }
.tag.noangle { background:rgba(245,158,11,.14); color:var(--amber); }
.tag.verdict { background:rgba(34,197,94,.14); color:var(--green); }
.tag.verdict.demoted_type_gate { background:rgba(245,158,11,.14); color:var(--amber); }
.undecided-note { border:1px solid var(--red); background:rgba(239,68,68,.08); color:var(--red); border-radius:8px; padding:9px 12px; font-size:13px; margin-bottom:10px; }
.err { border:1px solid var(--red); color:var(--red); border-radius:8px; padding:8px 12px; font-size:13px; }
.qgrade { display:inline-block; font-size:11px; font-weight:700; border-radius:4px; padding:0 6px; vertical-align:1px; }
.qgrade.a { background:rgba(34,197,94,.14); color:var(--green); }
.qgrade.b { background:var(--bg); border:1px solid var(--edge); color:var(--ink); }
.qgrade.c { background:var(--bg); border:1px solid var(--edge); color:var(--dim); }
.qgrade.d { background:rgba(245,158,11,.14); color:var(--amber); }
.qgrade.f { background:rgba(239,68,68,.14); color:var(--red); }
.vbtns { margin-top:7px; display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
.vbtn { font:inherit; font-size:12px; font-weight:600; padding:2px 11px; border-radius:5px;
  border:1px solid var(--edge); background:var(--bg); color:var(--dim); cursor:pointer; }
.vbtn:hover { color:var(--ink); }
.vbtn.good.on { background:rgba(34,197,94,.15); border-color:var(--green); color:var(--green); }
.vbtn.bad.on { background:rgba(239,68,68,.15); border-color:var(--red); color:var(--red); }
.vsaved { font-size:11px; color:var(--dim); }
</style>
</head>
<body>
<header>
  <div style="float:right;margin-top:2px"><a href="/" style="border:1px solid var(--edge);border-radius:6px;padding:4px 12px;font-size:12.5px;font-weight:600;display:inline-block">&larr; Home</a></div>
  <h1>INNOVATIVE HYPE &mdash; PIPELINE</h1>
  <div class="sub" id="subline"></div>
  <div class="chips" id="chips"></div>
</header>
<div class="grid">
  <div class="col col-k">
    <h2>Voice perspectives</h2>
    <div class="panel" id="vpersp"></div>
    <h2>Grade log</h2>
    <div class="panel" id="misses"></div>
    <h2>Keywords &middot; corpus seeds</h2>
    <div class="panel" id="seeds"></div>
    <h2>Corpus</h2>
    <div class="panel" style="overflow-x:auto"><table id="corpus"></table></div>
  </div>
  <div class="col">
    <h2>Clusters (14 in &rarr; desk)</h2>
    <div id="clusters"></div>
  </div>
  <div class="col">
    <h2>Run cards (out)</h2>
    <div id="undecidedNote"></div>
    <div id="cards"></div>
  </div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function hi(text, terms) {
  let out = esc(text);
  for (const t of terms.slice().sort((a,b)=>b.length-a.length)) {
    out = out.replace(new RegExp('\\\\b(' + t.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&') + '[a-z0-9\\'\\+-]{0,3})\\\\b','gi'), '<mark>$1</mark>');
  }
  return out;
}
const m = D.meta;
document.getElementById('subline').textContent =
  'run ' + D.run + ' \\u00b7 ' + (m.model||'?') + ' \\u00b7 code ' + (m.code_version||'?')
  + ' \\u00b7 desk ran ' + (m.timestamp||'?') + ' \\u00b7 page built ' + D.generated;
const T = D.totals;
document.getElementById('chips').innerHTML =
  [['clusters',T.clusters,''],['kept',T.kept,'var(--green)'],['type-gate demoted',T.demoted,'var(--amber)'],['UNDECIDED',T.undecided,'var(--red)'],['cards out',T.cards,'']]
  .map(([k,v,c]) => '<span class="chip"'+(c?' style="color:'+c+'"':'')+'><b>'+v+'</b> '+k+'</span>').join('');

// seeds
const seedEl = document.getElementById('seeds');
if (D.seed_error) seedEl.innerHTML = '<div class="err">'+esc(D.seed_error)+'</div>';
else seedEl.innerHTML = D.seeds.map(s => '<span class="seed">'+esc(s.term)+'</span>').join('')
  + '<div class="vw" style="margin-top:6px">lift-scored by scripts/brief.py: rate in the last 14 days vs everything older, from corpus/innovativehype + corpus/geoppls</div>';

// voice perspectives (stance + verbatim exemplars)
const vp = D.perspectives || {entries:[]};
const vpEl = document.getElementById('vpersp');
if (vp.error) vpEl.innerHTML = '<div class="err">'+esc(vp.error)+'</div>';
else if (!vp.entries.length) vpEl.innerHTML = '<div class="err">no perspective entries (run scripts/build_voice_profile.py)</div>';
else vpEl.innerHTML =
  '<div class="vw" style="margin-bottom:6px">built '+esc(vp.built||'?')+' from '+vp.n_posts+' posts; injected into the desk prompt verbatim</div>'
  + vp.entries.map(e =>
    '<div style="margin-bottom:9px"><b>'+esc(e.topic)+'</b> <span class="vw">'+esc(e.tone||'')+'</span>'
    + '<div style="font-size:12.5px;margin:2px 0">'+esc(e.stance)+'</div>'
    + (e.exemplars||[]).map(x => '<div class="vw" style="border-left:2px solid var(--edge);padding-left:7px;margin-top:3px">&ldquo;'+esc(x)+'&rdquo;</div>').join('')
    + '</div>').join('');

// grade feedback loop (runs/grades.jsonl; the desk prompt reads these back)
const ms = D.misses || [];
const msEl = document.getElementById('misses');
if (!ms.length) msEl.innerHTML = '<div class="vw">no D/F grades logged yet</div>';
else msEl.innerHTML =
  '<div class="vw" style="margin-bottom:6px">display only: nothing here feeds the desk prompt. The good/bad verdicts on each card are the judgment of record.</div>'
  + ms.map(m =>
    '<div style="margin-bottom:8px"><span class="qgrade '+esc((m.grade||'').toLowerCase())+'">'+esc(m.grade)+'</span> '
    + (m.angle ? '<span class="term">'+esc(m.angle)+'</span>' : '')
    + '<div style="font-size:12.5px;margin-top:3px">'+esc(m.narrative)+'</div>'
    + (m.note ? '<div class="vw">'+esc(m.note)+'</div>' : '')
    + '</div>').join('');

// corpus
document.getElementById('corpus').innerHTML =
  '<tr><th>file</th><th class="num">rows</th><th class="num">ids</th><th>newest</th></tr>'
  + D.corpus.map(r => '<tr><td>'+esc(r.file)+'</td><td class="num">'+r.rows+'</td><td class="num">'
    + (r.ids===r.rows ? r.ids : '<span class="flag">'+r.ids+'</span>')
    + '</td><td>'+r.newest+(r.flags.length?'<br><span class="flag">'+r.flags.map(esc).join(', ')+'</span>':'')+'</td></tr>').join('');

// clusters with highlighted keywords
document.getElementById('clusters').innerHTML = D.clusters.map(c =>
  '<div class="panel cluster '+esc(c.verdict)+'">'
  + '<span class="badge">'+esc(c.verdict)+'</span>'
  + '<div class="cname">'+esc(c.name)+' <span class="vw">\\u00b7 voice '+Number(c.voice_weight).toFixed(2)+'</span></div>'
  + '<div class="terms">'+c.terms.map(t=>'<span class="term">'+esc(t)+'</span>').join('')+'</div>'
  + c.items.map(it =>
      '<div class="item">'+(it.link?'<a href="'+esc(it.link)+'" target="_blank">'+hi(it.title,c.terms)+'</a>':hi(it.title,c.terms))
      + ' <span class="src">'+esc(it.source)+'</span>'
      + (it.excerpt?'<div class="ex">'+hi(it.excerpt,c.terms)+'</div>':'')+'</div>').join('')
  + '</div>').join('');

// cards
const un = D.clusters.filter(c=>c.verdict==='undecided');
document.getElementById('undecidedNote').innerHTML = un.length
  ? '<div class="undecided-note"><b>'+un.length+' rendered with NO decision row</b> \\u2014 cluster '
    + un.map(c=>'#'+c.index+' '+esc(c.name)).join('; ') + '. Gate bypass: fix before trusting the run.</div>' : '';
document.getElementById('cards').innerHTML = D.cards.map(c => {
  const cl = D.clusters[c.cluster_index] || {terms:[]};
  return '<div class="panel card">'
    + '<span class="tag '+(c.angle_id==='none'?'noangle':'verdict')+'">'+(c.angle_id==='none'?'no angle':esc(c.angle_id))+'</span>'
    + '<span class="tag verdict '+esc(c.verdict)+'">'+esc(c.verdict)+'</span>'
    + (c.grade ? '<span class="qgrade '+esc(c.grade.toLowerCase())+'" title="'+esc(c.grade_note||'')+'">'+esc(c.grade)+'</span>' : '')
    + '<div class="narr">'+hi(c.narrative,cl.terms)+'</div>'
    + '<div class="para">'+hi(c.paragraph,cl.terms)+'</div>'
    + (c.data_point?'<div class="dp">'+hi(c.data_point,cl.terms)+'</div>':'')
    + '<div class="vw">cluster #'+c.cluster_index+' \\u00b7 '+esc(c.name)+'</div>'
    + '<div class="vbtns" data-n="'+esc(c.narrative)+'" data-g="'+esc(c.grade)+'" data-k="'+esc(c.kicker||'')+'">'
      + '<button class="vbtn good" type="button">good card</button>'
      + '<button class="vbtn bad" type="button">bad card</button>'
      + '<span class="vsaved"></span>'
      + '</div>'
    + '</div>';
}).join('');

// manual verdicts (Micah 2026-08-27): his good/bad call is the judgment of
// record; the model grade is just a first-pass signal beside it. State
// persists in card_verdicts.jsonl via scripts/serve.py on this origin.
const verdicts = {};
function paintVerdicts() {
  document.querySelectorAll('.vbtns').forEach(box => {
    const v = (verdicts[box.getAttribute('data-n')] || {}).verdict;
    box.querySelector('.good').classList.toggle('on', v === 'good');
    box.querySelector('.bad').classList.toggle('on', v === 'bad');
    const ts = (verdicts[box.getAttribute('data-n')] || {}).ts;
    box.querySelector('.vsaved').textContent = ts ? ('saved ' + ts) : '';
  });
}
fetch('/api/verdicts').then(r => r.json()).then(d => {
  Object.assign(verdicts, d.verdicts || {});
  paintVerdicts();
}).catch(() => {}); // page opened without the API: buttons render, nothing persists
document.getElementById('cards').addEventListener('click', e => {
  const btn = e.target.closest('.vbtn');
  if (!btn) return;
  const box = btn.closest('.vbtns');
  const n = box.getAttribute('data-n');
  const v = btn.classList.contains('good') ? 'good' : 'bad';
  const next = (verdicts[n] || {}).verdict === v ? 'clear' : v;
  if (next === 'clear') delete verdicts[n];
  else verdicts[n] = {verdict: next, ts: 'saving…'};
  paintVerdicts();
  fetch('/api/verdict', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({narrative: n, verdict: next,
      grade: box.getAttribute('data-g'), kicker: box.getAttribute('data-k')})})
    .then(r => r.json())
    .then(d => {
      if (!d.ok) { box.querySelector('.vsaved').textContent = 'save failed'; return; }
      if (next === 'clear') { delete verdicts[n]; }
      else verdicts[n] = {verdict: next,
        ts: new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC'};
      paintVerdicts();
    })
    .catch(() => { box.querySelector('.vsaved').textContent = 'save failed'; });
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
