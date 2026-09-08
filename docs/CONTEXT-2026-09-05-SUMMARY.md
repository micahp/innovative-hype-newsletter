# 2026-09-05 - Innovative Hype news engine

Written 2026-09-07, covering 09-02 through 09-05. Read
`CONTEXT-2026-08-31-SUMMARY.md` first for the standing reds and the grader
rules. Commits in this window from this thread: `fe08da6`, `75130a7`,
`69116dc` (09-02), `248d498`, `6955b88` (09-04), `05ebac4`, `f1c6d9e`,
`0c1e042` (09-05). The `0aff2b0`..`063086a` run on 09-05 morning is the X
lane / desktop-pull work from a different session and is not covered here.

## THE WINDOW'S ONE SHAPE

**Three separate defects, and in all three the pipeline filled a gap with
something plausible instead of reporting the gap.**

1. An On3 subscription ad anchored the homepage hero, because the hero slot
   took the newest article by timestamp and never consulted the noise score
   that existed to catch exactly this.
2. Cards cited articles that had nothing to do with their claims, because
   when the source matcher found no match it fell back to the cluster's lead
   article, which by construction had just failed to match.
3. The desk wrote whole cards out of Micah's own old tweets, because the
   voice profile is injected into the cluster prompt as "his exact words"
   and those words contain real statistics.

Each produced a page that looked right. This is the same shape as
`.claude/skills/fail-loudly` §2, now with three more instances, and in
defect 2 the invented provenance is what hid defect 3 for weeks.

## 1. The ad on the hero (09-02)

`NOISE_PATTERNS` caught `$X off` and `discount|coupon|promo code`. On3's
"Get Gators Online for 75% off !!!" used `75% off` (no `$`) and "ANNUAL
MEMBERSHIPS", so it scored as clean news. Two more On3-network clones of the
same template were in the pool (K-State Online, Golden Bear Report).

The pattern gap was the small half. The real bug: `renderHero()` used
`filtered[0]`, the newest by timestamp, with no `_noise` check at all. Noise
capping only ever gated Top News. So even a correctly flagged ad could take
the hero, and on the Sports tab it still rendered as an ordinary card.

Fix: patterns extended, and `filterArticles()` now strips `_noise` articles
before anything downstream runs, so hero, Top News and every category grid
share one gate. 259 of 4,647 articles are noise-capped.

## 2. Section labels were internal analyst notes (09-02)

`NARRATIVE_SIGNATURES[].name` was doing double duty as the clustering key
AND the kicker printed on the card, so readers saw "Media power and who owns
it" and "The AI data gold rush".

Added `label` per signature (Media, Creator Economy, AI Infrastructure, AI
Safety, Housing, Surveillance, Sports Business, Prediction Markets, Crypto
Markets, Energy & Climate). **The `name` strings are unchanged and must stay
that way**: `gates.py:327`, `brief.py:382-390` and `voice_profile.json`
categories all match on them. Rename a label freely, never a name.

Also: the Brief now renders on every category tab, filtered by deriving each
card's category from the categories of the articles it cites.

## 3. Provenance: the desk was fabricating news (09-04)

Traced from one symptom, a card claiming AT&T routes 40% of employee AI
usage to open models while citing Fortune on Gen Z careers, CNBC on an
insurance merger, and Platformer on an AI writing clone.

**The cluster contained zero AT&T articles.** The claim came from
`voice_profile.json`, where Micah's own tweet carries those exact figures,
injected into the desk prompt at `narrative_desk.py:1658` as `his exact
words`. Five more cards ("models are converging", "open models closing the
gap") came from the same exemplar.

Two changes:

- `match_sources()` scores on **distinctive** shared vocabulary, not raw
  token overlap. Rarity is measured only when the cluster has >= 10 items,
  because in a 2-item cluster every subject word looks common and the one
  real source gets thrown away. Evidence required scales to how much choice
  the desk had: 0 hits for a one-off cluster (one article, provenance is
  structural), 1 under 10 items, 3 above.
- No match now **drops the card**. The fabricating fallback is gone, and
  `provenance` (distinctive_hits, required_hits, cluster_size) rides on each
  card so downstream can refuse what it cannot trace.

Measured over 331 cards from 40 runs: 322 traceable, 9 dropped, all 9
genuine fabrications, zero false rejections. False rejections were checked
specifically, since a gate that drops good cards is its own failure.

The prompt now labels exemplars register-only, but the gate is the actual
protection because it is mechanical rather than a request to the model.

### 3a. The fix looked done and the data disagreed

The gate ran at generation only. `merge_into_feed()` carries cards for
`FEED_MAX_AGE_H`, so the AT&T card returned to `brief-cards.json` hours
later with no `provenance` key at all, written by pre-gate code. The merge
now re-checks carried cards via `_cites_its_own_claim()`.

Also `_prov_tokens()` had to learn `&`: "AT&T" tokenised to `at` + `t`, both
under the 3-char floor, so the one word identifying the claim vanished and
the card looked like it was about "open models".

## 4. Social desk (09-05)

`scripts/social_desk.py` + `web/social.html`: each traceable story with both
card images, the 200-250 word post, a copy button, and its sources. This is
the copy-paste surface for Instagram and X.

- Photos come from the article's own `og:image`. Coverage is roughly 70-80%;
  On3 403s and CoinDesk 429s are the known datacenter-IP blocks. `og:image`
  is sometimes a **company logo rather than a photo**, which is unsolved.
- Post copy is written from the card's paragraph and data point only. The
  voice profile supplies register and is labelled as such in the prompt.
- Length is verified and retried. One ask for "200-250 words" returned 74 to
  158; three attempts with the count fed back gets 190-250.

### 4a. Card images

`scripts/make_card_image.py`, three styles, text composited with Pillow at
fixed pixel positions. **No diffusion model.** Micah's own framing was
"photoshop jobs, real photos with text overlaid", which is compositing.
Text is then exact and identical every run and costs nothing; fal's best
text models are $0.03-0.075/image and still not exact or deterministic.

- `bauhaus`: site palette, red kicker chip, paper plate.
- `mono`: the podcast cover identity (black, white lowercase Jost, corner
  wedge). Built from the real cover art at Buzzsprout feed 2194258.
- `hype` (default): built from reference accounts Micah supplied
  (@vesting, @edmmusic). Photo at 820px so it dominates, centred all-caps
  headline, figures auto-highlighted in yellow, no source credit.

Brand is from `logo.svg` and `/var/www/ih-src/v3.html`, not invented:
red `#e2231a`, yellow `#f4c300`, blue `#21409a`, paper `#f3f0e7`, ink
`#15140f`, Jost + Space Mono. Fonts vendored under `assets/fonts` (OFL).

Two corrections worth keeping: headline weight 800 was unreadable, 500 is
the cover's own weight; and **no card says "via TechCrunch"**, because
neither reference account credits the outlet on the artwork. The source
stays in `social.json` and on the page.

On the yellow: `#f4c300` is the site's existing token, and @vesting's
samples at `#f7c52d`. Same neighbourhood by coincidence of both being
Bauhaus primary yellow. The **technique** of colouring the figure is theirs.
If separation from them is wanted, the red is the more distinctive accent.

## 5. Voice profile was 9 days stale, and failing silently

`voice_profile.json` was built 08-27 while the collector kept running, so
the desk wrote in a 9-day-old voice. The rebuild had been failing: the
response hit `max_tokens=4000`, came back `finish_reason: length`, truncated
mid-JSON, and the parse raised a TypeError naming neither the cap nor the
truncation. Raised to 16000 and the failure now names the likely cause.

Rebuilt from 146 posts through 09-05. The window's topics are entirely
different from 08-27's: data centre water lies, AI as anti-DIY, US-Israel,
big agriculture, online privacy erasure. **Only 5 entries now, was 10.**
This also aged the AT&T exemplar out, removing the fabrication at its source.

Worth noting the profile is a 14-day window over a live corpus, so it is
load-bearing and perishable. It should be rebuilt on a schedule, not by hand.

## 6. Fail-loudly applied to this session's own code

The project skill surfaced late and indicted code written earlier the same
day. Fixed in `0c1e042`:

- `_pool_df()` deleted. It wrapped a read of `articles.json` in
  `except Exception: pass`, and after the entity rewrite nothing called it.
  Dead code with a silent-failure landmine in it, the §2a/2d shape exactly.
- `fetch()` returns `(ok, reason)`. A card with no `og:image` and one whose
  download 403'd looked identical, and only one is worth retrying.
- An empty `voice_profile.json` now raises. Posts with no register read like
  wire copy on a page that looks fine.
- Every run prints its counts, healthy or not: posts over cards attempted,
  images, no-photo, render errors, under-length, outright failures. An empty
  post list refuses to publish.

## 7. UNRESOLVED: the two provenance checks disagree

As of 09-07 the feed holds 52 cards, all carrying `provenance`, so the
generation gate is running in production and AT&T has not returned. But
`_cites_its_own_claim()` rejects 12 of those 52, including "Nvidia buys
Hugging Face for $13 billion", which is plainly a real story.

So the weaker legacy check has a false-positive class. Two known causes:
question-form headlines with no named subject ("Who actually owns the
culture now?") fall back to a 2-token overlap test, and entity matching by
capitalisation is crude. **Do not wire `_cites_its_own_claim()` into
anything that drops cards at render time until this is understood.** It is
currently only used on carried-forward pre-gate cards, which is the narrow
job it is good enough for.

## Next

- Reconcile the two provenance checks (§7). Start by measuring how many of
  the 12 are the question-headline class.
- `og:image` returns logos for some outlets; needs a fallback or a skip rule.
- G7 fails: 16 of 66 feeds dead. Pre-existing, untouched here, real.
- G2/G10 still in the spec and not in the runner. The runner now reports
  8/12 with 2 missing, so the denominator no longer shrinks to fit.
- Micah's open question: turn the MVP into a real site. Three pages
  (`index`, `brief`, `social`) grew separately and share no layout. The
  content pipeline is now more trustworthy than its presentation.
