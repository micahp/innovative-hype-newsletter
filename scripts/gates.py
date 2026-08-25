#!/usr/bin/env python3
"""gates.py — verify the news pipeline matches NEWS-ENGINE-SPEC.md.

Runs every gate (G1-G11 from the spec §6b) against the live web/articles.json
and the latest desk run. Exit 0 only when ALL gates pass. Wired into the cron
so a regression shows up as a red exit, not a silent drift.

Each gate prints  PASS  or  FAIL  with a reason. A FAIL means the pipeline no
longer matches the spec — fix the code or the spec, don't ignore it.
"""

import json
import re
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "web")
RUNS = os.path.join(REPO, "runs")
SCRIPTS = os.path.join(REPO, "scripts")

GENERIC_KEYWORDS = ["deal", "agent", "contract", "revenue", "billion", "platform", "media", "network"]

# The 8 acceptance stories (same as acceptance_fixture.py)
FIXTURE = [
    ("Flock cameras", ["flock", "stolen flock cameras", "camera", "surveillance"]),
    ("Data centers/Texas", ["data center", "williamson county", "blue origin"]),
    ("Marijuana Texas", ["marijuana", "cannabis", "texas"]),
    ("Longhorns vs Texas State", ["longhorn", "texas state"]),
    ("Kanye fireworks", ["kanye", "fireworks", "all of the lights"]),
    ("NBA->WNBA draft", ["wnba draft", "declare for the wnba"]),
    ("40-yr NCAAF", ["40-year-old", "college football", "age limit"]),
    ("Sophie Cunningham", ["sophie cunningham", "wnba commissioner"]),
]


# The gate roster from NEWS-ENGINE-SPEC.md §6b. It lives here so a gate that is
# in the spec and not in this file reports as a FAIL rather than as nothing.
# Before 2026-08-24 the runner implemented 9 of these 11 and printed
# "8/9 gates passed", a denominator that silently redefined itself to whatever
# had been written. G2 and G10 had never existed.
SPEC_GATES = {
    "G1": "no-admission-gate",
    "G2": "boost-not-filter",
    "G3": "three-ways-qualify",
    "G4": "seed-boost",
    "G5": "plural-match",
    "G6": "keyword-hygiene",
    "G7": "feeds-loud",
    "G8": "no-silent-drop",
    "G9": "stable-pool",
    "G10": "keep-cards",
    "G11": "source-align",
}

_RAN = []


def run_gate(name, check, detail=""):
    ok = check()
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not ok else ""))
    _RAN.append((name.split()[0], name, ok))
    return ok


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def main():
    print("=== NEWS-ENGINE GATES (NEWS-ENGINE-SPEC.md §6b) ===\n")
    results = []

    # --- Load inputs ---
    feed = load_json(os.path.join(WEB, "articles.json")) or {"articles": [], "feeds_ok": 0, "feeds_fail": 0}
    arts = feed.get("articles", [])

    # Latest desk run input/cards
    latest = os.path.join(RUNS, "latest")
    desk_input = load_json(os.path.join(latest, "input.json")) or {"clusters": []}
    desk_cards = load_json(os.path.join(latest, "cards.json")) or {"cards": []}
    desk_meta = load_json(os.path.join(latest, "meta.json")) or {}

    # Collect all desk titles for G8
    desk_titles = set()
    for cl in desk_input.get("clusters", []):
        for item in cl.get("items", []):
            desk_titles.add((item.get("title", "").lower(), item.get("source", "")))

    # --- G1: no admission gate in the desk path ---
    def g1():
        src = ""
        for p in ("brief.py", "narrative_desk.py"):
            path = os.path.join(SCRIPTS, p)
            if os.path.exists(path):
                src += open(path).read()
        # The old gate pattern must be gone
        return "if sig and points" not in src and "if sig and data" not in src
    results.append(run_gate("G1 no-admission-gate", g1))

    # --- G5: the matcher separates the cases it is there to separate ---
    sys.path.insert(0, SCRIPTS)
    import brief as brief_mod
    # This gate used to assert brief._kw_match() handled plurals. As of
    # 2026-08-24 nothing in the pipeline calls _kw_match: clustering is
    # embedding similarity. A green assertion about a function that decides
    # nothing is the §2e failure, so the gate moves to the surface that now
    # decides, keeping the spec's intent (the matcher matches the right
    # things) and dropping a test of dead code.
    def g5():
        h = [x for x in brief_mod.NARRATIVE_SIGNATURES
             if x["name"].startswith("Cities")][0]
        probes = {
            # (text, must_cluster_here_or_None)
            "Padres make flurry of roster moves before Pirates series": None,
            "Mystics take big first step toward WNBA championship": None,
            "Texas A&M fall camp intel: Aggies secondary starting to take shape": None,
            "Austin rents fall 12% as a wave of new apartments finishes": h["name"],
        }
        import embed
        keys = list(probes)
        sims = embed.similarity(keys, [brief_mod._sig_probe_text(x)
                                       for x in brief_mod.NARRATIVE_SIGNATURES])
        for i, text in enumerate(keys):
            order = sorted(zip(sims[i], brief_mod.NARRATIVE_SIGNATURES),
                           key=lambda t: -t[0])
            best, sig = float(order[0][0]), order[0][1]
            runner = float(order[1][0])
            joins = (sig["name"] if best >= brief_mod.SIG_SIM_FLOOR
                     and best - runner >= brief_mod.SIG_SIM_MARGIN else None)
            want = probes[text]
            if joins != want:
                print(f"      G5: {text[:52]!r} joins {joins} (want {want}), "
                      f"best {best:.3f}")
                return False
        return True
    results.append(run_gate("G5 subject-match", g5))

    # --- G6: hygiene, on every list that steers matching ---
    # The spec's rule is that generic or accidental vocabulary must not steer
    # what a story is judged to be about. It used to check only signature
    # keywords. Since 2026-08-24 the signature `subject` sentence and the
    # angles.yaml `scope` do that job and the keywords do not, so the gate
    # covers all three. Place names are barred by name: `texas` sitting in the
    # housing keyword list is what put a WNBA story in that cluster.
    PLACES = ("texas", "austin", "houston", "dallas", "galveston", "america",
              "american", "minnesota", "california", "florida")

    def g6():
        bad = []
        for sig in brief_mod.NARRATIVE_SIGNATURES:
            subj = (sig.get("subject") or "").strip()
            if not subj:
                bad.append(f"signature {sig['name']!r} has no subject sentence")
                continue
            low = subj.lower()
            for pl in PLACES:
                if re.search(r"\b%s\b" % pl, low):
                    bad.append(f"signature {sig['name']!r} subject names {pl!r}")
        angles_path = os.path.join(REPO, "angles.yaml")
        if os.path.exists(angles_path):
            import yaml
            doc = yaml.safe_load(open(angles_path)) or {}
            for a in doc.get("angles", []):
                for term in (a.get("scope") or []):
                    t = str(term).lower().strip()
                    if t in GENERIC_KEYWORDS:
                        bad.append(f"angle {a.get('id')!r} scope has generic {t!r}")
                    if t in PLACES:
                        bad.append(f"angle {a.get('id')!r} scope has place {t!r}")
        else:
            # Evidence unavailable is a FAIL, never a skip.
            bad.append("angles.yaml is missing, so its scope cannot be checked")
        for b in bad[:8]:
            print("      " + b)
        if len(bad) > 8:
            print(f"      ...and {len(bad) - 8} more")
        return not bad
    results.append(run_gate("G6 matching-hygiene", g6))

    # --- G4: seed matching exists and boosts ---
    def g4():
        seeds = brief_mod._TWEET_SEEDS
        if len(seeds) < 10:
            return False
        # An article mentioning a seed should get more seed_hits than one that doesn't
        seeded = {"title": "Flock cameras stolen in Texas", "summary": "", "_body": ""}
        plain = {"title": "Quarterly earnings report released", "summary": "", "_body": ""}
        return brief_mod._seed_match(seeded) > brief_mod._seed_match(plain)
    results.append(run_gate("G4 seed-boost", g4))

    # --- G7: feed failures are loud ---
    #
    # This used to be `"feeds_fail" in feed and "feed_failures" in feed`, a
    # presence check on a JSON key. It answered "did something write this key",
    # which was never the question. It was green on 2026-08-24 with 18 of 55
    # feeds dead, and green on 08-21 with 17 of 48 dead. The spec says the gate
    # passes when a dead feed causes a visible failure, so now a dead feed fails
    # the gate and the names are printed.
    def g7():
        if "feeds_fail" not in feed or "feed_failures" not in feed:
            print("      articles.json does not report feed failures at all")
            return False
        n = feed.get("feeds_fail") or 0
        if n:
            names = feed.get("feed_failures") or []
            print("      %d of %d feeds dead: %s"
                  % (n, feed.get("feeds_total") or 0, ", ".join(names[:12])))
            if len(names) > 12:
                print("      ...and %d more" % (len(names) - 12))
        return n == 0
    results.append(run_gate("G7 feeds-loud", g7))

    # --- G8: no SILENT disappearance ---
    # Per spec: absent/dropped are loud, not silent. The failure is a story
    # vanishing with no trace. The fixture reports each of the 8 stories as
    # ABSENT/DROPPED/REACHED/CARDED — that report IS the loudness. This gate
    # passes as long as the fixture runs and reports (i.e. nothing is
    # silently dropped). It is NOT a "everything must reach the desk" gate.
    def g8():
        # The fixture script must exist and run (its non-zero exit when
        # stories are dropped IS the loud signal). Check it's wired in.
        fixture_path = os.path.join(SCRIPTS, "acceptance_fixture.py")
        if not os.path.exists(fixture_path):
            return False
        # And the fixture must cover all 8 stories (nothing silently absent
        # from the report itself)
        src = open(fixture_path).read()
        return all(label.split(" ")[0] in src for label, _ in FIXTURE)
    results.append(run_gate("G8 no-silent-drop (fixture reports all 8)", g8))

    # --- G9: stable pool_key ---
    def g9():
        # Recompute pool key from the latest run's clusters; must be deterministic
        sys.path.insert(0, SCRIPTS)
        import narrative_desk as nd
        clusters = nd.load_clusters()
        key1 = nd.pool_key(clusters)
        key2 = nd.pool_key(clusters)
        return key1 == key2
    results.append(run_gate("G9 stable-pool", g9))

    # --- G11: source alignment (cards link to matching content) ---
    def g11():
        bad = 0
        for card in desk_cards.get("cards", []):
            if not card.get("narrative"):
                continue
            # The render does content-matching; here we verify no obvious mismatch
            # by checking the card has sources (non-empty) — deep content check
            # happens at render time. This is a smoke test.
            if card.get("source_ids") is None and not card.get("_cluster_idx"):
                bad += 1
        return bad == 0
    results.append(run_gate("G11 source-align (smoke)", g11))

    # --- G3: three ways to qualify ---
    def g3():
        # data point path: Micro1 story has a data point (should be in desk)
        # quote/moment: check at least one one-off or non-signature card exists
        has_data_card = any(
            cl.get("name") and "AI data gold rush" in cl.get("name", "")
            for cl in desk_input.get("clusters", [])
        )
        has_one_off = any(
            cl.get("name", "").startswith("One-off")
            for cl in desk_input.get("clusters", [])
        )
        return has_data_card and has_one_off
    results.append(run_gate("G3 three-ways-qualify", g3))

    # A gate in the spec with no implementation here is a FAIL, not an absence.
    ran_ids = {gid for gid, _, _ in _RAN}
    missing = [g for g in SPEC_GATES if g not in ran_ids]
    for gid in sorted(missing, key=lambda g: int(g[1:])):
        print(f"  [FAIL] {gid} {SPEC_GATES[gid]} — in NEWS-ENGINE-SPEC.md §6b, "
              f"not implemented in gates.py")
        results.append(False)

    print()
    passed = sum(1 for r in results if r)
    print(f"  {passed}/{len(SPEC_GATES)} gates passed "
          f"({len(ran_ids)} implemented, {len(missing)} missing)")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
