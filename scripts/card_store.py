#!/usr/bin/env python3
"""card_store.py — the durable card store (Phase 2).

Phase 1's failure, measured 2026-08-26: the brief was a 72-hour sliding
window that happened to render. 693 distinct cards had been written across
all runs; 35 were live; 658 existed nowhere on the site and no stage of the
pipeline ever read them again. `narrative_desk.py:610` dropped them by not
copying them into `out`.

Phase 2 changes exactly one thing: nothing is dropped. Every card the desk
writes gets a row in `cards.jsonl` on every run in which it appears, and a
card that stops rendering is a STATE (`aged_out`, `evicted`), not an absence.
Nothing in the pipeline deletes a row.

The store is the LOG. The current state of a card is its newest row.

CLI:
    python3 scripts/card_store.py --rebuild    reconstruct from runs/*
    python3 scripts/card_store.py --counts     print current counts

This module is imported by narrative_desk.py (write-through) and gates.py
(G12). It must therefore import nothing heavier than stdlib.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(REPO, "runs")
STORE_PATH = os.path.join(REPO, "cards.jsonl")

STATES = ("live", "aged_out", "evicted", "removed")
# `removed` is reserved for the Phase 3 judgment interface. Nothing writes it
# yet; it is defined now so the interface does not have to migrate the schema.


# --------------------------------------------------------------- identity

def _tokens(text):
    return set(re.findall(r"[a-z']{4,}", (text or "").lower()))


def resolve_sources(card, items):
    """Replica of narrative_desk.render_brief_html source resolution.

    story_key is sha256 of the sorted source URLs of the three top-scoring
    same-cluster articles (overlap >= 2 card tokens), deduped by publisher,
    falling back to the cluster lead item when nothing overlaps. This MUST
    match production keying or rebuilt keys will not line up with live ones —
    if narrative_desk changes how it keys sources, change this in the same
    commit (fail loudly: two identities for one card is worse than none).
    """
    ct = _tokens(f"{card.get('narrative', '')} {card.get('paragraph', '')}")
    scored = []
    for sid, item in enumerate(items):
        title = item.get("title") or ""
        scored.append((len(ct & _tokens(title)), sid, item))
    scored.sort(key=lambda x: -x[0])
    picks, seen = [], set()
    # Production gate: only articles sharing >= 2 content tokens qualify,
    # and only the THREE highest-scoring candidates are considered. This
    # replication must stay exact or rebuilt keys diverge from live keys.
    for ov, sid, it in scored[:3]:
        if ov < 2:
            continue
        src = it.get("source") or ""
        if src in seen:
            continue
        seen.add(src)
        picks.append({"source": src,
                      "url": it.get("link") or "#",
                      "headline": title})
        if len(picks) >= 3:
            break
    if not picks and items:
        lead = items[0]
        picks = [{"source": lead.get("source") or "",
                  "url": lead.get("link") or "#",
                  "headline": lead.get("title") or ""}]
    return picks


def story_key_of(sources):
    """The canonical story_key: sha256 of sorted source URLs, 16 hex chars."""
    urls = sorted(x["url"] for x in sources)
    if not urls:
        return None
    return hashlib.sha256("|".join(urls).encode()).hexdigest()[:16]


# ------------------------------------------------------------------- io

def read_rows(path=STORE_PATH):
    """Every row in the store, oldest first.

    Fail loudly: an unreadable or corrupt store RAISES rather than starting
    empty. A silent empty return makes the live brief look exactly like a
    healthy one with a small pool (the §2a/§2d failure shape), so this
    function has no except-and-default path at all.
    """
    rows = []
    if not os.path.exists(path):
        return rows
    ln = 0
    try:
        with open(path) as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(
            f"card store {path} is unreadable at line {ln}: {e}. "
            f"Refusing to start from an empty store; fix it or run "
            f"`scripts/card_store.py --rebuild`.") from e
    return rows


def latest_by_key(rows):
    """Newest row per story_key, plus enough metadata for state decisions."""
    out = {}
    for i, r in enumerate(rows):
        k = r.get("story_key")
        if k:
            cur = out.get(k)
            # Rows are appended chronologically per run; same-run duplicates
            # keep the later (which carried forward first_seen, last_seen).
            if cur is None or i > cur["_i"]:
                r = dict(r)
                r["_i"] = i
                out[k] = r
    return out


def append_rows(rows, path=STORE_PATH):
    """Append-only write. Never truncates, never rewrites existing lines."""
    with open(path, "a") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def count_state(rows=None):
    """Return {live: N, aged_out: N, evicted: N, removed: N, total: N} over
    the newest row of each distinct story_key."""
    if rows is None:
        rows = read_rows()
    latest = latest_by_key(rows)
    counts = {s: 0 for s in STATES}
    for r in latest.values():
        st = r.get("state")
        if st not in counts:
            counts[st] = counts.get(st, 0) + 1
        else:
            counts[st] += 1
    counts["total"] = len(latest)
    counts["_rows"] = len(rows)
    return counts


def say_counts(prefix="", rows=None):
    """Rule 5: say the counts every run. Print even the zeros."""
    c = count_state(rows)
    print(f"{prefix}{c['live']} live, {c['aged_out']} aged_out this store, "
          f"{c['evicted']} evicted, {c['total']} total "
          f"({c['_rows']} rows)")
    return c


# ------------------------------------------------------------ write path

def record_run(new_cards, state_overrides=None, run_ts=None, store_path=STORE_PATH):
    """Write through every card feed() just processed.

    new_cards: dicts as produced by merge_into_feed/render_brief_html —
      story_key, kicker, narrative, paragraph, data_point, sources,
      source_count, lead_score, voice_weight, soft_penalty, first_seen,
      updated.
    state_overrides: {story_key: "evicted"} for cards declined on THIS run;
      everything still rendering defaults to "live".

    Rule 4: zero rows against a non-empty store raises.
    """
    prev_rows = read_rows(store_path)
    prev_latest = latest_by_key(prev_rows)
    now = run_ts or datetime.now(timezone.utc).isoformat()

    to_write = []
    keys_this_run = set()
    for c in new_cards:
        k = c.get("story_key")
        if not k:
            continue
        if k in keys_this_run:
            continue
        keys_this_run.add(k)
        prev = prev_latest.get(k)
        fs = c.get("first_seen")
        if not isinstance(fs, str) or not fs:
            fs = prev.get("first_seen") if prev else now
        row = {
            "story_key": k,
            "run": now,
            "first_seen": fs,
            "last_seen": now,
            "state": ((state_overrides or {}).get(k)) or "live",
            "narrative": c.get("narrative", ""),
            "paragraph": c.get("paragraph", ""),
            "kicker": c.get("kicker", ""),
            "sources": c.get("sources") or [],
            "angle_id": c.get("angle_id"),
            "angle_offered": c.get("angle_offered"),
            "lead_score": c.get("lead_score"),
        }
        to_write.append(row)

    if prev_rows and not to_write:
        raise RuntimeError(
            "card_store.record_run would write ZERO rows against a non-empty "
            f"store ({len(prev_rows)} rows, {len(prev_latest)} keys). "
            "A silently empty write looks identical to a healthy small pool. "
            "Fix the run before storing anything.")

    append_rows(to_write, store_path)

    # State transitions for keys ABSENT this run are recorded by writing a new
    # row (append-only: never rewrite history). Idempotent: a key whose newest
    # row is already aged_out does not get another copy every run — the
    # transition happened once, the log records it once.
    aged = evicted_recheck = 0
    from datetime import datetime as _dt, timedelta as _td
    cutoff = _dt.now(_tzutc()) - _td(hours=_feed_max_age_h())
    skip_keys = set(keys_this_run)
    for k, prow in prev_latest.items():
        if k in skip_keys:
            continue
        if prow.get("state") == "aged_out":
            continue
        try:
            seen = _dt.fromisoformat(prow.get("first_seen"))
        except Exception:
            seen = None
        if seen is None or seen < cutoff:
            new_row = dict(prow)
            new_row.pop("_i", None)
            new_row["run"] = now
            new_row["last_seen"] = now
            new_row["state"] = "aged_out"
            to_write.append(new_row)
            aged += 1
    if aged:
        append_rows(to_write[len(to_write) - aged:], store_path)

    n_new = len(to_write) - aged
    print(f"  STORE wrote {n_new} card row(s); marked {aged} aged_out "
          f"(not seen for >{_feed_max_age_h()}h)")
    # Monotonicity ledger (read by gates.G12): one tiny row recording how many
    # rows existed BEFORE this call. Appended last so the NEXT run reads it
    # as its previous count. Lives in the store itself, not a fixture.
    append_rows([{"_prev_row_count": len(prev_rows), "run": now,
                  "note": "row-count ledger for gates.py G12"}], store_path)
    say_counts(prefix="  STORE now: ")
    return len(to_write)


def _tzutc():
    return timezone.utc


def _feed_max_age_h():
    # Mirror narrative_desk.FEED_MAX_AGE_H without importing the desk (no
    # heavy deps, no circular import). Same env var wins.
    return float(os.environ.get("IH_FEED_MAX_AGE_H", "72"))


# -------------------------------------------------------------- rebuild

def rebuild(store_path=STORE_PATH):
    """Reconstruct the whole store from runs/*/cards.json + input.json.

    Identity join: replica of render_brief_html source resolution. Cards whose
    cluster index was lost by older code get a token-overlap re-alignment to
    their own run's clusters (recorded but flagged, see CLI output).

    Fail loudly: any corrupted snapshot raises with its path rather than being
    skipped; a rebuild producing zero rows raises instead of writing an empty
    store.
    """
    paths = sorted(p for p in glob.glob(os.path.join(RUNS, "2*"))
                   if os.path.isdir(p))
    rows_out = []
    per_run, recovered, unrecoverable = [], 0, []
    for p in paths:
        cp, ip, mp = p + "/cards.json", p + "/input.json", p + "/meta.json"
        if not all(os.path.exists(x) for x in (cp, ip)):
            continue
        try:
            cards = json.load(open(cp)).get("cards", [])
            clusters = json.load(open(ip)).get("clusters", [])
        except (OSError, json.JSONDecodeError) as e:
            raise RuntimeError(f"rebuild: corrupt snapshot in {p}: {e}") from e
        meta = {}
        if os.path.exists(mp):
            try:
                meta = json.load(open(mp))
            except Exception:
                meta = {}
        run_ts = meta.get("timestamp") or \
            datetime.strptime(os.path.basename(p), "%Y%m%d_%H%M%S") \
                    .replace(tzinfo=timezone.utc).isoformat()
        wrote = 0
        for c in cards:
            if not c.get("narrative"):
                continue
            ci = c.get("_cluster_idx")
            realigned = False
            if not (isinstance(ci, int) and 0 <= ci < len(clusters)):
                ci = c.get("cluster_index")
            if not (isinstance(ci, int) and 0 <= ci < len(clusters)):
                bci, bs = _realign(c, clusters)
                if bci is None:
                    unrecoverable.append((os.path.basename(p),
                                          c.get("narrative", "")[:60]))
                    continue
                ci, realigned = bci, True
                recovered += 1
            items = clusters[ci].get("items") or []
            sources = resolve_sources(c, items)
            k = story_key_of(sources)
            if not k:
                continue
            angles_offered = _angles_for_cluster(clusters, ci, p)
            rows_out.append({
                "story_key": k,
                "run": run_ts,
                "first_seen": run_ts,   # refine after chronological sort
                "last_seen": run_ts,
                "state": "aged_out",
                "narrative": c.get("narrative", ""),
                "paragraph": c.get("paragraph", ""),
                "kicker": (clusters[ci].get("sig") or {}).get("name", "")
                          if clusters[ci].get("sig") else
                          (items[0].get("category", "").title() if items and
                           items[0].get("category") else ""),
                "sources": sources,
                "angle_id": c.get("angle_id"),
                "angle_offered": angles_offered,
                "lead_score": None,   # not recoverable from snapshots
            })
            wrote += 1
        per_run.append((os.path.basename(p), wrote))

    if not rows_out:
        raise RuntimeError("rebuild produced ZERO rows from runs/*; refusing "
                           "to replace the store with emptiness.")

    # Chronological stitch BEFORE any write. Replaying what the store WOULD
    # have recorded run by run: a row is "live" if the card was inside
    # FEED_MAX_AGE_H of its true first_seen at that run's time — which is
    # exactly what merge_into_feed used to decide (silently) whether to copy
    # a card forward. Keys whose newest row predates the current cutoff get
    # an explicit aged_out TRANSITION row appended, stamped now, so state on
    # the newest row always answers "where is this card now".
    rows_out.sort(key=lambda r: (r["run"], r["story_key"]))
    from datetime import datetime as _dt, timedelta as _td
    maxage_h = _feed_max_age_h()
    now_iso = datetime.now(timezone.utc).isoformat()
    firsts = {}
    for r in rows_out:
        k = r["story_key"]
        if k not in firsts or r["run"] < firsts[k]:
            firsts[k] = r["run"]
    n_live = n_aged = 0
    for r in rows_out:
        k = r["story_key"]
        # Phase-1 semantics: every row of a card carries the card's ORIGINAL
        # first_seen (what merge_into_feed always carried forward). Rows
        # synthesized here get the true origin too, not their own run ts.
        r["first_seen"] = firsts[k]
        try:
            fs = _dt.fromisoformat(firsts[k])
            rt = _dt.fromisoformat(r["run"])
        except Exception:
            fs = rt = None
        if fs is None or rt is None or (rt - fs) <= _td(hours=maxage_h):
            r["state"] = "live"
            n_live += 1
        else:
            r["state"] = "aged_out"
            n_aged += 1

    # Present-tense transitions for keys that have since fallen out of the
    # window, so no query ever mistakes staleness for liveness.
    cutoff = _dt.now(timezone.utc) - _td(hours=maxage_h)
    lasts = {}
    for r in rows_out:
        k = r["story_key"]
        if k not in lasts or r["run"] > lasts[k]["run"]:
            lasts[k] = r
    transitions = []
    for k, r in lasts.items():
        if r["state"] != "aged_out":
            try:
                ls = _dt.fromisoformat(r["last_seen"])
            except Exception:
                continue
            if ls < cutoff:
                t = dict(r)
                t["run"] = now_iso
                t["last_seen"] = now_iso
                t["state"] = "aged_out"
                transitions.append(t)
    for t in transitions:
        t.pop("_i", None)
    rows_out.extend(transitions)

    tmp = store_path + ".rebuild.tmp"
    with open(tmp, "w") as f:
        for r in rows_out:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    # Row-count ledger for gates.G12 (reads the store itself, not a fixture).
    with open(tmp, "a") as f:
        f.write(json.dumps({"_prev_row_count": len(rows_out),
                            "run": now_iso,
                            "note": "row-count ledger for gates.py G12"},
                           sort_keys=True) + "\n")
    os.replace(tmp, store_path)

    keys = len({r["story_key"] for r in rows_out})
    print(f"REBUILD: {len(paths)} candidate run dirs, "
          f"{sum(w for _, w in per_run)} cards written back")
    print(f"  -> {store_path}: {len(rows_out)} rows, {keys} distinct cards")
    print(f"  replayed {n_live} live / {n_aged} aged_out rows as they would "
          f"have been recorded; {len(transitions)} aged_out transition(s) "
          f"appended for cards out of the window as of now")
    if recovered:
        print(f"  note: {recovered} card(s) re-aligned to clusters by token "
              f"overlap (their snapshots predate _cluster_idx)")
    if unrecoverable:
        print(f"  note: {len(unrecoverable)} card(s) could not be joined to a "
              f"cluster and are NOT in the store:")
        for rn, t in unrecoverable[:5]:
            print(f"    {rn}: {t}")
    csay = say_counts(prefix="  store now: ")
    return len(rows_out), keys, csay


def _realign(card, clusters):
    tokens = _tokens(f"{card.get('narrative', '')} {card.get('paragraph', '')}")
    if not tokens:
        return None, 0.0
    best, bs = None, 0.0
    for ci, cl in enumerate(clusters):
        clt = set()
        for it in cl.get("items", []):
            clt |= _tokens(it.get("title") or "")
        if not clt:
            continue
        ov = len(tokens & clt) / float(len(tokens | clt))
        if ov > bs:
            best, bs = ci, ov
    if best is not None and bs >= 0.05:
        return best, bs
    return None, 0.0


_ANGLES_CACHE = {}


def _angles_for_cluster(clusters, ci, run_dir):
    """Best-effort angle ids that were legal for a cluster. Snapshots' input.json
    may carry angle_offered per cluster when the desk recorded it."""
    cl = clusters[ci]
    ao = cl.get("angle_offered") or cl.get("angles") or []
    return list(ao) if ao else None


# ------------------------------------------------------------------ cli

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true",
                    help="reconstruct cards.jsonl from runs/*/cards.json")
    ap.add_argument("--counts", action="store_true",
                    help="print current store counts")
    args = ap.parse_args()

    if args.rebuild:
        rebuild()
        return 0
    if args.counts:
        say_counts()
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
