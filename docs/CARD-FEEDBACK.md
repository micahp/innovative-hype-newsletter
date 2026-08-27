# CARD FEEDBACK — Micah's individual card rulings

Running log of Micah's verdicts on individual cards. Newest first. Each entry:
the card, his call, his words (lightly cleaned), and what changed in the system
because of it. His good/bad button clicks from the pipeline page live in
`card_verdicts.jsonl`; they get folded in here when he asks or when relevant.

Standing rules these entries established:
- Grades never move a card's rank and never auto-feed the desk prompt.
- His verdict is the judgment of record; the model grade is a first-pass signal.

---

## 2026-08-27 — "The old gatekeepers of culture are falling away..." (CREATOR ECONOMY CONSOLIDATION)

**Verdict:** reporting good, messaging beneath him.

He likes what the card reports on (SoundCloud direct artist sales, CAA indie
games fund, Roy Price microdramas) but calls the messaging childish: hype-man
motivational framing. Model grade was B.

**His words:** "i like what its repotting on but the messaging isbbeneath me.
chikdish almost."

**Changed:** grader rubric now treats hype-man / motivational register as a
voice failure (C/D even with good reporting). He is hype-RESISTANT; cheerleading
is the opposite of his voice and is graded down.

## 2026-08-27 — "AI leaders have failed at messaging..." (AI TRUST AND ACCOUNTABILITY)

**Verdict:** F. It is a self-contradiction.

The paragraph's facts (agents trained to cheat, hack, Alabama subpoena) are
real and serious; the thesis and the closing sentence spin them into
calm-down framing ("leaving the public with a scarier picture than the reality
of a test gone wrong"). He called it a paradox: wrong title, wrong angle, wrong
last sentence. Model grade kept saying D/B.

**His words:** "its a fucking F! ... it literally contradicts itself. read the
paragraph its a paradox... all you have to do is read the paragraph and its
clear thats the wrong title and angle/last sentence."

**Changed:** grader now reads the paragraph against the thesis line by line;
internal contradiction and calm-down reframe are F regardless of reporting
quality. Root cause also logged: this headline was a canned angles.yaml claim
(ai-messaging-failure) stamped over contradicting facts.

## 2026-08-27 — "OpenAI's own agents hacked Hugging Face..." headline

**Verdict:** the longer, more specific version from a previous run was better.

He does not like generalizing without being specific. The current headline
names Hugging Face and Alabama; a prior run's headline carried more of the
specific story and he preferred it. Across-run rewrites must not trade
specific anchors (companies, people, numbers) for generalized frames.

**Changed:** desk prompt gains a rewrite rule: cut color, never facts; keep
the concrete anchors on every rewrite.

## 2026-08-27 — "Raising kids in the AI age..." (BUSINESS)

**Verdict:** good card; the F was an instrument error.

He asked how it could be an F. The F was phantom: its citation mis-resolved to
a Texas Tribune school-takeover piece and the source essay (MIT TR "Raised on
AI") had rolled out of the grading window, so the grader judged a parenting
card against a schools article.

**Changed:** story-context resolution now searches archived runs (~48h) and
matches by phrase overlap; cited sources can never drive a grade.

## 2026-08-27 — "Tech workers keep their kids off social media..." (AI TRUST AND ACCOUNTABILITY)

**Verdict:** A, regardless of what the grader says.

The grader graded it F, then D, then C ("one parent's experience, not a
systemic claim"). He knows the big-tech-parents pattern and says the card is
actually an A. His call stands.

**Changed:** this is the card that triggered the manual good/bad buttons: his
verdict is the judgment of record, the model grade is a signal beside it.
