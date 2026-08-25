#!/usr/bin/env python3
"""embed.py - the semantic-similarity primitive for this pipeline.

Why this exists
---------------
Three separate layers of this engine decided what a story was ABOUT by counting
substring hits from a hand-written keyword list:

  brief.NARRATIVE_SIGNATURES   which cluster a story joins
  voice_terms.txt              the fourth ranking term
  angles.yaml  scope           which position the desk may take on a cluster

Measured 2026-08-24, the failure mode is identical in all three. The housing
signature is keyed on `texas`, so a Blue Origin rocket factory in Williamson
County reads as a story about where Americans live. `texas` also took 55 of the
150 voice-term hits. And 53 of 62 angles were never once eligible, because
their scope only contained words Micah happened to type.

A keyword list cannot be tuned out of this. Broadening it attaches everything;
tightening it attaches nothing. Both failures are real and they are the same
mechanism, which is that a word is not a subject.

This module matches on MEANING instead: text goes to an embedding model, and
similarity is the cosine between vectors. A story about hyperscaler leasing
matches a position about renting your compute forever with no shared words.

Fail-loudly contract (.claude/skills/fail-loudly)
------------------------------------------------
This is a pipeline input, not optional data. Every failure path here raises:
a missing key, a provider error, a short batch, a zero vector. There is no
`return []`. An embedding layer that silently returns nothing would turn every
similarity to zero, no angle would ever be eligible, and the brief would look
exactly the same as a healthy one.

Cache
-----
Vectors are cached on disk keyed by sha256(model + text), so a rerun over a
2,000-article pool costs only the articles that changed. The cache is derived
data and is safe to delete.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.environ.get("IH_EMBED_CACHE", os.path.join(REPO, ".embed-cache"))

MODEL = os.environ.get("IH_EMBED_MODEL", "openai/text-embedding-3-small")
DIMS = 1536
PROVIDER_BASE = "https://inference-api.nousresearch.com/v1"
BATCH = 64
MAX_CHARS = 8000  # ~2k tokens; enough for a title + mined points or a claim

_mem = {}
_stats = {"asked": 0, "cache_hits": 0, "fetched": 0, "batches": 0}


def _api_key():
    """Same key as narrative_desk.call_llm. Raises rather than degrading."""
    key = os.environ.get("NOUS_PORTAL_KEY", "")
    if not key:
        env_path = "/root/.hermes/.env"
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("NOUS_PORTAL_KEY="):
                    key = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    if not key:
        raise RuntimeError(
            "No NOUS_PORTAL_KEY in the environment or /root/.hermes/.env. "
            "Every similarity would be undefined without it, so this raises "
            "instead of returning zero vectors that read as 'nothing matches'.")
    return key


def _cache_path(text):
    h = hashlib.sha256((MODEL + "\x00" + text).encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, h[:2], h + ".npy")


def _fetch(batch):
    """One /embeddings call. Raises on anything short or malformed."""
    body = json.dumps({"model": MODEL, "input": batch}).encode()
    req = urllib.request.Request(
        PROVIDER_BASE + "/embeddings", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + _api_key(),
                 "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ih-embed/1.0"})
    # 429/500/502/503/504 are the provider being busy, which is not a fact
    # about our data: retry those. A 400/401/403/404 is a permanent refusal
    # (bad key, bad model id, malformed body) and retrying it just burns time,
    # so it raises on the first response.
    data, last = None, None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode())
            break
        except urllib.error.HTTPError as e:
            detail = e.read()[:400].decode("utf-8", "replace")
            if e.code not in (429, 500, 502, 503, 504):
                raise RuntimeError("embeddings HTTP %s (permanent): %s"
                                   % (e.code, detail))
            last = "HTTP %s: %s" % (e.code, detail)
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)
        if attempt < 3:
            wait = 2 ** attempt
            print("  embeddings transient (%s); retry %d/3 in %ds"
                  % (last, attempt + 1, wait))
            time.sleep(wait)
    if data is None:
        raise RuntimeError(
            "embeddings failed after 4 attempts: %s. Returning zero vectors "
            "here would score 0.0 against everything and read as 'nothing "
            "matches', so this raises." % last)
    rows = data.get("data") or []
    if len(rows) != len(batch):
        raise RuntimeError(
            "embeddings returned %d vectors for %d inputs. A short batch would "
            "silently misalign every vector with the wrong text."
            % (len(rows), len(batch)))
    rows.sort(key=lambda r: r.get("index", 0))
    out = []
    for r in rows:
        v = np.asarray(r["embedding"], dtype=np.float32)
        if v.shape[0] != DIMS or not np.isfinite(v).all() or not v.any():
            raise RuntimeError(
                "embeddings returned a bad vector (shape %s, all-zero=%s). A "
                "zero vector scores 0.0 against everything, which reads as "
                "'no match' rather than as a failure." % (v.shape, not v.any()))
        out.append(v / np.linalg.norm(v))
    _stats["batches"] += 1
    return out


def embed(texts):
    """L2-normalised vectors for `texts`, in order. Cached on disk."""
    texts = [(t or "").strip()[:MAX_CHARS] for t in texts]
    if any(not t for t in texts):
        raise ValueError(
            "embed() got an empty string. An empty subject means an upstream "
            "stage produced nothing, and embedding it would hide that.")
    _stats["asked"] += len(texts)

    out = [None] * len(texts)
    todo, todo_ix = [], []
    for i, t in enumerate(texts):
        if t in _mem:
            out[i] = _mem[t]
            _stats["cache_hits"] += 1
            continue
        p = _cache_path(t)
        if os.path.exists(p):
            v = np.load(p)
            _mem[t] = v
            out[i] = v
            _stats["cache_hits"] += 1
            continue
        todo.append(t)
        todo_ix.append(i)

    for s in range(0, len(todo), BATCH):
        chunk = todo[s:s + BATCH]
        vecs = _fetch(chunk)
        for t, v, i in zip(chunk, vecs, todo_ix[s:s + BATCH]):
            p = _cache_path(t)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            np.save(p, v)
            _mem[t] = v
            out[i] = v
            _stats["fetched"] += 1
    return out


def warm(texts):
    """Pre-fetch vectors for many texts, batched.

    similarity() is called once per article by signature_for() and once per
    cluster by eligible_angles(). Without this each of those calls fetches a
    batch of one, so a 400-article pool costs 400 sequential round trips.
    Callers warm the whole pool first and every per-item call is then a cache
    hit.
    """
    texts = [t for t in ((x or "").strip()[:MAX_CHARS] for x in texts) if t]
    if not texts:
        return
    embed(sorted(set(texts)))


def similarity(a_texts, b_texts):
    """Cosine matrix, len(a) x len(b). Vectors are already normalised."""
    A = np.vstack(embed(a_texts))
    B = np.vstack(embed(b_texts))
    return A @ B.T


def stats_line():
    """Say the zero. Printed by every caller, healthy run or not."""
    return ("embeddings: %d asked, %d cached, %d fetched in %d batches (%s)"
            % (_stats["asked"], _stats["cache_hits"], _stats["fetched"],
               _stats["batches"], MODEL))


if __name__ == "__main__":
    probe = sys.argv[1:] or [
        "Williamson County greenlights a $674M Blue Origin rocket factory",
        "Nvidia turns compute into an asset class with $500 billion in financing",
        "Marc Lore sells the Minnesota Timberwolves for $4.5 billion",
    ]
    ref = ["housing affordability and where Americans can afford to live",
           "you will never own your compute, you will rent it forever",
           "sports franchise valuations keep inflating"]
    M = similarity(probe, ref)
    for i, p in enumerate(probe):
        print("\n" + p[:76])
        for j, r in enumerate(ref):
            print("   %.3f  %s" % (M[i][j], r[:64]))
    print("\n" + stats_line())
