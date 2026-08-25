#!/usr/bin/env python3
"""angle_coverage.py - which angles can ever fire, measured against the pool.

consolidate_angles.py produced 378 live positions from ten years of writing.
That is a real inventory and it is not an editable one, and its shape is
lopsided: 2021-22 was the volume peak of the X archive, so NFT-era positions
outnumber anything about how the feed reads today.

The old instrument for this question was nothing. 53 of 62 angles in the
previous inventory had never been eligible once across 758 cards, and there was
no way to know that without reading every decisions.json by hand.

This is the instrument. Every angle is scored against every article in the live
pool with the same cosine the desk uses, and the answer is how many stories it
could reach. An angle that reaches zero is a position he holds that this feed
will never carry, which is a fact about the feed, not a judgment about the
position.

    python3 scripts/angle_coverage.py             # ranked table
    python3 scripts/angle_coverage.py --dead      # only the unreachable ones
    python3 scripts/angle_coverage.py --top 40    # the cut list, as YAML ids
"""
import argparse
import json
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import embed  # noqa: E402
import brief  # noqa: E402
import narrative_desk as nd  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANGLES = os.path.join(REPO, "angles.yaml")
POOL = os.path.join(REPO, "web", "articles.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dead", action="store_true", help="only unreachable angles")
    ap.add_argument("--top", type=int, default=0, help="print the N best as ids")
    ap.add_argument("--limit", type=int, default=1200, help="articles to score")
    args = ap.parse_args()

    angles = nd.load_angles()
    doc = yaml.safe_load(open(ANGLES))
    print("angles:   %d enabled of %d" % (len(angles), len(doc.get("angles", []))))

    if not os.path.exists(POOL):
        raise FileNotFoundError(
            "%s is missing, so coverage cannot be measured. Reporting every "
            "angle as reachable would be worse than reporting nothing." % POOL)
    arts = [a for a in json.load(open(POOL))["articles"] if not a.get("_noise")]
    arts = arts[:args.limit]
    print("pool:     %d articles" % len(arts))

    subjects = []
    for a in arts:
        pts = brief.mine_data_points(a)
        s = brief.signature_subject_text(a, pts)
        if s:
            subjects.append((s, a.get("title", "")))
    embed.warm([s for s, _ in subjects] + [nd.angle_probe_text(x) for x in angles])
    print("  " + embed.stats_line())

    A = np.vstack(embed.embed([nd.angle_probe_text(x) for x in angles]))
    S = np.vstack(embed.embed([s for s, _ in subjects]))
    M = A @ S.T  # angles x articles

    floor = nd.ANGLE_SIM_FLOOR
    rows = []
    for i, ang in enumerate(angles):
        reach = int((M[i] >= floor).sum())
        j = int(np.argmax(M[i]))
        rows.append((reach, float(M[i][j]), ang["id"], subjects[j][1]))
    rows.sort(key=lambda r: (-r[0], -r[1]))

    dead = [r for r in rows if r[0] == 0]
    print("\nreachable: %d angles reach at least one story at cosine >= %.2f"
          % (len(rows) - len(dead), floor))
    print("dead:      %d reach nothing in this pool" % len(dead))

    show = dead if args.dead else rows
    if args.top:
        for r in rows[:args.top]:
            print(r[2])
        return 0
    print("\n%-5s %-6s %-44s %s" % ("reach", "best", "angle", "nearest story"))
    for reach, best, aid, title in show[:80]:
        print("%-5d %.3f  %-44s %s" % (reach, best, aid[:44], title[:44]))
    if len(show) > 80:
        print("... and %d more" % (len(show) - 80))
    return 0


if __name__ == "__main__":
    sys.exit(main())
