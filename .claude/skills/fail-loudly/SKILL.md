---
name: fail-loudly
description: MUST load before touching score_article(), gates.py, any file the pipeline READS as configuration (voice_terms.txt, angles.yaml, the corpus, the feed list), any try/except around a load, or any run that writes web/articles.json. Encodes the one shape behind this pipeline's defects, which is that a broken input produces a plausible brief and the run reports healthy. Triggers on "it ranked fine", "best-effort", a bare except around a read, a term or keyword list, a gate that checks a key exists, a default value, "why is this empty", and on any claim that a run was clean.
---

# Fail loudly (Innovative Hype news engine)

Load this before writing anything that can partially succeed.

It exists because on 2026-08-24 an audit found the fourth ranking term, the
highest-leverage thing on the project, in a state where it could have been
contributing nothing and every instrument would still have said the run was
fine.

---

## 1. The governing principle

> **A system that degrades instead of failing does not have fewer bugs. It has
> the same bugs, undiscovered, plus the time you spent not finding them.**

The tell is always the same: **the output is plausible.** A brief with seven
cards in it looks exactly like a brief with seven cards in it. Nothing about
the artifact tells you whether the selection ran.

The stakes are specific here. Per `docs/CONTEXT-2026-08-23-SUMMARY.md` §WHY,
this engine is judged on **whether the selection matches the person**, not on
whether the prose is clean. Every silent degradation in this file degrades the
selection while leaving the prose untouched, which is the one failure mode the
reader cannot see and the author will not report.

---

## 2. The measured cases

### 2a. The configuration file that fails to load turns a score term off

`_load_voice_terms()` wrapped the whole read in `except Exception: return []`,
at import time. Rename `voice_terms.txt`, break a line in it, run from a
directory that resolves the relative path differently, and the fourth score
term becomes zero for every article. No error. No log line. Every story ranks
exactly as it did before the term was written, which is a state we already know
produces a golf ad at #1.

> **Rule.** A file the pipeline reads as CONFIGURATION is not optional data.
> When it fails to load, say so on stdout with the reason, and carry the reason
> into the run meta. An empty parse is the same failure as a missing file.

### 2b. Nothing measured which entries of the list were doing anything

52 voice terms. On the 2,022-article pool of 2026-08-24, **24 of them fired
zero times**, including `palantir`, `thc`, `hemp`, `marijuana`, `deepseek`,
`cursor`, `elon musk` and `zuckerberg`. Those are the exact subjects the term
was added to rescue, and the commit that added it cites "Texas THC lawsuit #419
to #1" as its evidence. Meanwhile `texas` alone took 55 of the 150 hits.

A dead line and a line doing all the work are indistinguishable from outside
the run. The list looks curated either way.

> **Rule.** Any list that influences ranking must report per-entry hit counts
> and an explicit dead list, every run. A curated list nobody measures decays
> into a list of good intentions.

### 2c. The run's self-description outlived the formula

`score_article()` gained a fourth term. `articles.json` kept announcing
`"name": "weighted_editorial_v1"` with the three old terms and no mention of
the boost, the cap, or the term file. A stored `articles.json` therefore could
not tell you which scorer produced it.

> **Rule.** The meta block names the formula that ran. Change the formula,
> change the name, and put the new term's parameters beside it. This is the
> local form of "record what you generated FROM": a run that cannot say what it
> was is a run you cannot compare against another one.

### 2d. The corpus that IS the specification lived in /tmp

`extract_angles.py` defaulted `ARCHIVE_JSON` to a path inside a Claude session
scratchpad, and `load_archive_originals()` returned `[]` when the file was
gone. That archive is 33,143 tweets, the thing `VOICE-AND-WORLDVIEW.md` was
mined from. An empty return means every extracted position quietly disappears
and the extractor still completes.

> **Rule.** If losing an input would invalidate the output, the missing input
> raises. It does not return an empty list. And it does not live outside the
> repo.

### 2e. A gate that checks a key EXISTS is not checking the thing

G7 in `NEWS-ENGINE-SPEC.md` §6b is "feeds-loud", and it must pass only when
`feeds_fail > 0 causes non-zero exit / visible failure`. What `gates.py`
actually asserts is:

```python
return "feeds_fail" in feed and "feed_failures" in feed
```

That is a presence check on a JSON key. On 2026-08-24 the feed was
`feeds_ok 37, feeds_fail 18, total 55`, so a third of the sources were dead,
and G7 was green. It has been green through every measurement of dead feeds
this project has ever taken, including the 17-of-48 recorded on 08-21.

> **Rule.** Read what the assertion asserts, not what the gate is named. A gate
> that checks presence answers "did something write this key", which is never
> the question anyone had.

### 2f. Gates that are in the spec and not in the runner count as neither

§6b lists eleven gates, G1 through G11. `gates.py` runs nine. **G2
(boost-not-filter) and G10 (keep-cards) do not exist in the runner**, and the
summary line prints `8/9 gates passed`, a denominator that silently redefines
itself to whatever was implemented.

> **Rule.** The runner enumerates the spec's gate list and reports a missing
> gate as a FAIL, not as an absence. A denominator that shrinks to fit is not a
> measurement.

### 2g. A hygiene rule enforced on one list, while a second list has the same job

G6 bans generic keywords from signatures by name: `deal`, `agent`, `contract`,
`revenue`, `billion`, `platform`, `media`, `network`. `voice_terms.txt` was
added later, does the same job (it moves articles up the ranking), and contains
`platform`, `compute`, `privacy`, `lawsuit` and `jury`. G6 passes, because G6
only looks at signatures. `platform` then put "WildBrain Acquires Kid Safe
Generative-AI Platform Personality AI" at #6.

> **Rule.** When you add a second input that does an existing input's job,
> extend that input's gate to cover it in the same commit. A rule enforced on
> one surface only is not enforced.

---

## 3. Writing it so it fails loudly

1. **Zero is a finding.** `0 terms loaded`, `0 articles boosted`, `0 feeds ok`
   must each print differently from a healthy run. A log that only speaks up on
   failure cannot tell "clean" from "never ran".
2. **Say the zero.** Print every count even when it is fine, including the dead
   lists. `52 loaded, 28 fired, 24 dead` is a fact you can diff next week.
3. **Never `except: pass` or `except: return []` around a read.** Catch, record
   the reason, carry it into the meta.
4. **Count both sides.** `150 of 2,022 articles boosted` is a fact. "the voice
   term is working" is not.
5. **Fail closed on "cannot check".** Evidence unavailable is a FAIL, never a
   skip and never a pass.
6. **The gate is a claim about its surface.** All 9 running gates were green
   through every defect in §2.

---

## 4. Before you call it done

- Name the loud failure you added, with the mechanism. Not "added error
  handling".
- If the change can partially succeed, say what it prints when it does.
- Run `python3 scripts/gates.py` and read the assertions of any gate you are
  relying on, rather than its name.
- If you added a ranking input, say which existing gate you extended to cover
  it, or why none applies.
