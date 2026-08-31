# 2026-08-27 - Innovative Hype news engine

Written 2026-08-30 (session ran 08-27). Read `CONTEXT-2026-08-26-SUMMARY.md`
first: this one assumes v0.1.0, the numpy/cron interpreter split, and the
grader that existed before it.

Five commits: `ad30fa0` (grader story-context + manual verdicts), `4ec4abe`
(topic-gap feeds), `4c46e7e` (contradiction/hype-man rubric + rewrite rule),
`b802d21` (gated outlets via gnews + sitemaps), `6ff949a` (artifacts). Pushed.

## THE DAY'S ONE SHAPE

**The instruments graded the citation, not the story.** Every phantom grade
Micah caught this session was the grader judging the card against the wrong
text: a mis-resolved URL, a source that had already aged out of the corpus, a
"cited sources" block that outweighed the story context, and a thesis its own
paragraph contradicted. Fixing the rubric was the last 10%; fixing WHAT THE
GRADER READ was the other 90%.

## 1. Grader trust repair (his "how was this an F?")

The card he flagged ("Raising kids in the AI age...", graded F, actually good)
failed three ways at once, all fixed in `ad30fa0` + `4c46e7e`:

1. **Story context resolution** (`narrative_desk.grade_feed`): cluster index
   first, then best match in the current run, then best match across the 24
   newest ARCHIVED run inputs (~48h) — feed cards outlive the corpus window.
   Match = stopworded unigram + 3x bigram overlap, floor `MIN_CTX_OV = 14`.
   Below the floor is NO context, not weak context.
2. **CITED SOURCES can never drive a grade.** The resolver is frequently
   wrong; the rubric now says STORY CONTEXT is authoritative and the cited
   block is annotated "may be mis-matched; ignore if unrelated".
3. **Two new F/D rules from his rulings** (all logged in
   `docs/CARD-FEEDBACK.md`, created this session on his request):
   - INTERNAL CONTRADICTION IS AN F: read the paragraph against the thesis;
     a calm-down reframe over serious facts ("scarier picture than the
     reality of a test gone wrong") is an F. His ai-leaders card now grades
     F with a note that says exactly why.
   - HYPE-MAN REGISTER IS A VOICE FAILURE (C/D): he is hype-RESISTANT;
     "now is the time for anyone to go make something" is beneath him. His
     sarcasm and stances are never graded down.
   - SPECIFICITY: an abstract-trend thesis with no concrete anchors caps at
     D, and a REWRITE may not trade anchors for abstraction (desk prompt
     rule: cut color, never facts).

Standing rules, re-established: grades never move rank, never auto-feed the
desk prompt, display + log only. His verdict is the judgment of record.

## 2. Manual good/bad buttons (pipeline page)

`scripts/serve.py` (ThreadingHTTPServer :8099, replaces plain http.server;
tunnel unchanged): POST `/api/verdict` {narrative, verdict good|bad|clear,
grade, kicker} appends to `card_verdicts.jsonl` (repo root); GET
`/api/verdicts` returns latest-wins per narrative. Optimistic UI, re-click =
clear. Verdicts are a LOG ONLY — nothing feeds them back automatically.

## 3. Coverage audit (his Q1: does the corpus cover what I tweet?)

Method: LLM topic pass over 14d of his tweets, then word-boundary regex
against `web/articles.json` titles with RFC2822-parsed dates.

Instrument traps, both real: `datetime.fromisoformat` parsed 40 of 3,274
RFC2822 `published` values (use `email.utils.parsedate_to_datetime`), and
substring matching makes "ai" hit every title and "heir" hit "their".

Result: everything covered except Kanye/Yeezy (true zero, Vibe added),
MLS/soccer thin (BBC Football added), and "nepotism in tech darlings" (his
exact frame; generic inequality keywords found nothing; BI + Fortune carry
it). Also fixed Wired's URL and swapped frozen feeds. feeds_ok 37 to 42.

## 4. Gated JUST IN outlets (his Q2 + "archive.ph or wayback machine")

The desks' upstream (Bloomberg, Reuters, Axios, WSJ, CNN, AP) had no free
RSS. Probed once each per the call policy: Reuters 401, Axios 403,
Bloomberg 403, AP/CNN serve HTML (RSS is what's gated). The archive
direction was the dead end: archive.ph 429 from this box, and Wayback's
Reuters/Bloomberg section snapshots ARE the 401/403 gate pages.

What worked (`b802d21`):
- **Google News RSS** for Reuters/Axios/Bloomberg:
  `news.google.com/rss/search?q=site%3A<host>+when:2d...` returns 100 fresh
  items each. Rows are HEADLINE-ONLY by design: Google's summary is an
  anchor to its own redirect page (blanked, not stored), titles get the
  " - Outlet" suffix stripped, links are JS interstitials so the body
  fetcher skips them (counted loudly: "5 gnews items skipped").
- **News sitemaps** for AP/CNN (both answer 200): `apnews.com/
  news-sitemap-content.xml` (627 URLs), `cnn.com/sitemap/news.xml` (225).
  Publisher's own titles + REAL article URLs + ISO dates, so trafilatura's
  top-15 fetch can reach their pages: full-text capable. Filters: /video/,
  non-English (AP ships Spanish), cnn-underscored commerce.
- Date parse: strptime %z NEVER accepts "GMT" (all Google pubDates);
  `parsedate_to_datetime` fallback added before calling a date undated.
- Old dead "Reuters Business" feed removed. 46/66 feeds OK.

**His full-articles question, answered honestly:** most pool rows are
headline + <=300-char summary. Full text = content:encoded feeds, or
top-15-ranked + fetchable page. Reuters/Axios/Bloomberg stay headline-only
from this box (walls are site-wide); AP/CNN go full-text when they rank.

## 5. Standing reds (both pre-existing, both unchanged by this session)

- Acceptance fixture 1/8 reached the desk, identical before and after the
  feed work. The drops are time-window drops of old named stories; Kanye
  fireworks and NBA-to-WNBA draft are older than the 72h pool.
- Gates 8/12: G2 (boost-not-filter) and G10 (keep-cards) exist in the spec,
  are not implemented in gates.py, and the runner says so in its summary.

## Next

- Watch a 2h cron cycle with the new surfaces live (Google occasionally
  returns a valid-EMPTY result set for a working query; it reads as a FAILED
  feed and the cron retries — correct and loud).
- Fold button verdicts from `card_verdicts.jsonl` into CARD-FEEDBACK.md when
  he asks.
- WSJ Markets feed (feeds.a.dj.com) is configured but frozen at Jan 2025;
  either drop it or find a fresh surface.
