#!/usr/bin/env python3
"""consolidate_angles.py - turn raw extracted candidates into angles.yaml.

extract_angles.py reads 2,772 posts in batches of 120 and asks for at most 20
positions per batch. Across 24 batches that is up to 480 candidates, and
merging them by exact id barely dedupes: the same position comes back as
`you-will-never-own-your-compute` in one batch and `renting-your-compute` in
the next. The first run produced 488.

488 rows is not an inventory anyone can hand-edit, and it is not what the desk
should choose from. This is the second pass:

  1. GROUP mechanically. Every candidate is embedded and near-identical ones
     are grouped by cosine. This is the part a model should not be doing by
     hand across a 488-row list, and it is exact and free.

  2. MERGE by model, one call per batch of groups. The model sees a group of
     candidates that are already known to be the same position and writes the
     single best statement of it, with the extrapolated subject line and a
     scope covering the category.

  3. DROP what cannot fire on news. The corpus runs back to 2016 and holds
     real positions about, for instance, how up-and-coming musicians should
     network. Those are genuinely his and they will never match a story in
     this feed. The model is asked to say so rather than the inventory
     carrying 400 rows that can never be eligible.

    python3 scripts/consolidate_angles.py
    python3 scripts/consolidate_angles.py --dry-run
"""
import argparse
import json
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import embed  # noqa: E402
import narrative_desk as nd  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(REPO, "angles.candidates.yaml")
OUT = os.path.join(REPO, "angles.yaml")

# Cosine at which two candidates are the same position. Measured on the 487
# candidates from the 2026-08-24 extraction: nearest-neighbour cosine is p50
# 0.581, so most candidates genuinely have no duplicate and grouping alone can
# never do the reduction. At 0.86 it made 483 groups from 487. At 0.66 it makes
# 424 and the merges it does make are right: five Flock-camera statements
# become one, five AI-and-jobs statements become one.
#
# The reduction comes from the model instead, in two places: the `live` flag
# drops positions no news story can trigger (the corpus runs to 2016 and holds
# real, permanent positions about how up-and-coming musicians should network),
# and a second round regroups the survivors, whose rewritten claims sit much
# closer together than the raw candidates did.
SAME_POSITION = float(os.environ.get("IH_ANGLE_DEDUPE", "0.66"))
GROUPS_PER_CALL = 20
ROUNDS = 2

_SYSTEM = (
    "You are consolidating a raw list of positions extracted from one "
    "person's writing into the inventory a newsroom will actually use. Micah "
    "Peoples writes Innovative Hype, covering tech, business, sports and "
    "culture.\n"
    "\n"
    "Each GROUP below holds candidates an embedding model already judged to be "
    "the same position, stated in different words. For each group, write the "
    "ONE position it represents:\n"
    "  id      — short kebab-case slug\n"
    "  claim   — ONE sentence in his voice stating the position, at the level "
    "he would defend it. One level above the story that provoked it: 'the "
    "housing market in Galveston is oversupplied' is an observation about one "
    "town and is worthless next week; the position underneath it applies to "
    "any market.\n"
    "  subject — ONE sentence naming the CATEGORY the position is about, "
    "written so it stays true when the subject turns up under names he never "
    "used. A position about Nvidia renting you compute is about renting versus "
    "owning the infrastructure you depend on, which also covers hyperscaler "
    "leasing, inference pricing and on-device models.\n"
    "  scope   — 6 to 12 lowercase terms naming things that BELONG TO that "
    "category, including ones he never used. These are read by an embedding "
    "model, not matched as substrings. Never a place name unless the position "
    "is genuinely about that place.\n"
    "  evidence — 1 to 3 short quotes carried over from the candidates.\n"
    "  live    — true if a news story could plausibly trigger this position in "
    "a feed covering tech, business, AI, markets, sports, media and cities. "
    "false if it is a real position that no news story will ever be about, "
    "such as advice to up-and-coming musicians about networking.\n"
    "\n"
    "RULES: exactly one position per group, in the same order as the groups. "
    "Never merge two groups. Never invent a position no candidate states. "
    "Marking something false is expected and useful: say so rather than "
    "widening its subject until it looks newsworthy.\n"
    'Output STRICT JSON: {"positions": [{"id": "...", "claim": "...", '
    '"subject": "...", "scope": ["..."], "evidence": ["..."], "live": true}]}'
)


def probe(c):
    parts = [c.get("claim", "")]
    if c.get("subject"):
        parts.append(c["subject"])
    parts.append("Subjects: " + ", ".join(c.get("scope") or []) + ".")
    return " ".join(parts).strip()


def load_candidates():
    if not os.path.exists(CAND):
        raise FileNotFoundError(
            "%s is missing. Run scripts/extract_angles.py first. Writing "
            "angles.yaml from nothing would replace the inventory with an "
            "empty file and every card would be written position-free." % CAND)
    doc = yaml.safe_load(open(CAND)) or {}
    rows = [a for a in doc.get("angles", []) if a.get("claim") and a.get("scope")]
    if not rows:
        raise RuntimeError("%s parsed to 0 usable candidates." % CAND)
    return rows


def group(cands):
    """Greedy grouping by cosine. Each candidate joins the first group whose
    seed it is within SAME_POSITION of, else it seeds a new group."""
    V = np.vstack(embed.embed([probe(c) for c in cands]))
    groups, seeds = [], []
    for i, c in enumerate(cands):
        placed = False
        if seeds:
            sims = np.vstack(seeds) @ V[i]
            j = int(np.argmax(sims))
            if float(sims[j]) >= SAME_POSITION:
                groups[j].append(c)
                placed = True
        if not placed:
            groups.append([c])
            seeds.append(V[i])
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cands = load_candidates()
    print("candidates:      %d" % len(cands))
    groups = group(cands)
    print("groups:          %d  (cosine >= %.2f is the same position)"
          % (len(groups), SAME_POSITION))
    print("  " + embed.stats_line())
    sizes = sorted((len(g) for g in groups), reverse=True)
    print("  largest groups: %s" % sizes[:8])
    print("  singletons:     %d" % sum(1 for s in sizes if s == 1))

    def consolidate(items, label):
        """One round: group by cosine, then one model call per batch of
        groups. Returns (kept, dropped)."""
        gs = group(items)
        print("%s: %d in -> %d groups" % (label, len(items), len(gs)))
        kept, cut = [], []
        for st in range(0, len(gs), GROUPS_PER_CALL):
            chunk = gs[st:st + GROUPS_PER_CALL]
            lines = []
            for gi, g in enumerate(chunk):
                lines.append("GROUP %d:" % gi)
                for c in g[:6]:
                    lines.append("  - claim: %s" % c.get("claim", ""))
                    if c.get("subject"):
                        lines.append("    subject: %s" % c["subject"])
                    lines.append("    scope: %s" % ", ".join(c.get("scope") or []))
                    for e in (c.get("evidence") or [])[:2]:
                        lines.append("    evidence: %s" % str(e)[:200])
            raw = nd.call_llm(_SYSTEM, "\n".join(lines), max_tokens=8000)
            try:
                got = json.loads(raw).get("positions", [])
            except Exception as exc:
                # A batch that fails to parse loses every position in it. Name
                # the groups so a rerun is not guesswork.
                print("    PARSE FAILED groups %d-%d (%s); %d groups lost"
                      % (st, st + len(chunk), exc, len(chunk)))
                continue
            for pz in got:
                if not pz.get("id") or not pz.get("claim") or not pz.get("scope"):
                    continue
                (cut if pz.get("live") is False else kept).append(pz)
            print("    groups %3d-%3d -> %3d live, %3d not live"
                  % (st, st + len(chunk),
                     sum(1 for x in got if x.get("live") is not False),
                     sum(1 for x in got if x.get("live") is False)))
        return kept, cut

    out, dropped = consolidate(cands, "round 1")
    for r in range(2, ROUNDS + 1):
        # The survivors' rewritten claims sit much closer together than the raw
        # candidates did, so a second pass merges what the first could not see.
        before = len(out)
        out, cut2 = consolidate(out, "round %d" % r)
        dropped.extend(cut2)
        print("round %d: %d -> %d" % (r, before, len(out)))
        if len(out) >= before:
            print("  no further reduction; stopping")
            break

    merged = {}
    for p in out:
        aid = p["id"].strip().lower()
        if aid in merged:
            merged[aid]["scope"] = sorted(set(merged[aid]["scope"])
                                          | set(x.lower() for x in p["scope"]))
        else:
            merged[aid] = {"id": aid, "claim": p["claim"],
                           "subject": (p.get("subject") or "").strip(),
                           "scope": [x.lower().strip() for x in p["scope"]],
                           "evidence": (p.get("evidence") or [])[:3]}

    print("\nkept:            %d live positions" % len(merged))
    print("dropped:         %d that no news story can trigger" % len(dropped))
    for p in dropped[:12]:
        print("   - %s" % p.get("claim", "")[:88])
    if len(dropped) > 12:
        print("   ... and %d more" % (len(dropped) - 12))

    if not merged:
        raise RuntimeError(
            "0 live positions from %d candidates in %d groups. Writing that to "
            "angles.yaml would leave the desk with no position to take on any "
            "story, and the brief would still look finished."
            % (len(cands), len(groups)))

    doc = {
        "_readme": (
            "The angle inventory. Generated by scripts/extract_angles.py then "
            "scripts/consolidate_angles.py, and edited by hand after that. An "
            "angle fires on a story whose SUBJECT matches it, by embedding "
            "similarity against claim + subject + scope, not by keyword. Edit "
            "freely: delete positions that are not yours, rewrite a subject "
            "that is catching the wrong stories, set enabled: false to retire "
            "one without losing it. decisions.json records the angle offered "
            "on every cluster with its score, so when a card picks badly you "
            "can point at the row and the number."),
        "angles": [
            {"id": a["id"], "enabled": True, "claim": a["claim"],
             "subject": a["subject"], "scope": a["scope"],
             "evidence": a["evidence"]}
            for a in merged.values()],
    }
    text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=88)
    if args.dry_run:
        print("\n" + text)
        return 0
    with open(OUT, "w") as f:
        f.write(text)
    print("wrote %s" % OUT)
    print("EDIT IT. These are candidates read off the corpus, not your ruling.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
