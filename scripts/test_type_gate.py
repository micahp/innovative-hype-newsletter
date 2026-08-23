#!/usr/bin/env python3
"""The type gate: expected values committed BEFORE the classifier can drift.

Micah, 2026-08-21: "how many cards are we just gonna be talking about how
womens sports has good players and there playing well??? thats like 4 cards".
The prompt has asked the model to decline these since that day and it declines
unreliably, so the rule lives in code. These cases are the contract.

The two DECLINE-side cases are real headlines the desk actually shipped on
2026-08-23. The KEEP-side cases are the stories Micah named as the ones the
engine must never lose. Several of them are WNBA or college-football stories
full of performance vocabulary, which is the whole reason the gate is
two-sided: a one-sided keyword ban on sports words would throw away exactly
what he asked for.

    python scripts/test_type_gate.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from narrative_desk import performance_only  # noqa: E402


DECLINE = [
    # Shipped 2026-08-23 and should not have been.
    "Angel Reese's career-high 31 points also made Dream history.",
    "Who will be Alabama's starting quarterback this season?",
    "Marina Mabrey ties the WNBA single-game scoring record with 53 points.",
    "The X-Factor: Kaitlyn Chen's meteoric rise off the bench.",
    "Leading by Example: Marina Mabrey is becoming a star in Toronto.",
    "Basketball Without Borders brings 40 top high-school players to Chicago.",
    "Alabama names Keelon Russell starting quarterback for the season opener.",
    # Roster churn. All three shipped 2026-08-23 and are the same no-story type:
    # recruiting, transfers and staff moves are not a conversation.
    "Why did Donovan Dent commit to LSU?",
    "Linebacker Ty'Anthony Smith leaves Texas football program before the season",
    "Bob Chesney's UCLA is poaching Sun Belt DPOY Trent Hendricks",
]

KEEP = [
    # From Micah's named list, 2026-08-21. Every one of these is a sports
    # story, and every one must survive the gate.
    "Sophie Cunningham says the WNBA commissioner should be fired next year.",
    "Judge rules players can go from NFL training camp back to college.",
    "A 40-year-old is playing NCAA football after an eligibility ruling.",
    "NBA players are declaring for the WNBA draft.",
    "Newest WNBA dildo thrower arrested and banned.",
    # Roster vocabulary with a real ruling behind it must still survive.
    "A judge granted Mark Mitchell a fifth year of eligibility.",
    # Money, ownership and power stories that use performance vocabulary.
    "Marc Lore sells the Timberwolves for $4.5 billion.",
    "The US Open raises prize money to a record $108 million after a player protest.",
    "Key NFL committees clear the way for the $9.6 billion Seahawks sale.",
    # Not sports at all; must never be caught by a sports-word ban.
    "Flock's new AI police tool can track drivers without a license plate.",
    "TikTok pays $400 million to settle child-privacy charges.",
]


class TypeGateTests(unittest.TestCase):
    def test_declines_performance_only(self):
        for text in DECLINE:
            with self.subTest(text=text):
                self.assertTrue(
                    performance_only(text),
                    "should be declined as performance-only: " + text)

    def test_keeps_everything_with_a_power_angle(self):
        for text in KEEP:
            with self.subTest(text=text):
                self.assertFalse(
                    performance_only(text),
                    "must NOT be declined; it has a power angle: " + text)

    def test_no_performance_vocabulary_is_never_declined(self):
        # The gate is opt-in: a card with no performance markers at all is not
        # its business, whatever else it says.
        self.assertFalse(performance_only("Hutto is becoming a company town."))
        self.assertFalse(performance_only(""))
        self.assertFalse(performance_only(None))


class DedupeTests(unittest.TestCase):
    """Two publishers covering one event must not become two cards.

    Shipped 2026-08-23: two Good Good Golf ad cards in the same feed. The feed
    key is a hash of source URLs, so the same story from two clusters gets two
    keys. Token overlap alone did not catch it (the paraphrases shared only
    "good" and "golf"), so the subject of the headline decides.
    """

    def test_same_subject_collapses(self):
        from narrative_desk import dedupe_feed
        out = dedupe_feed([
            {"narrative": "Good Good Golf deletes a violent ad while Callaway stays silent"},
            {"narrative": "Good Good Golf removes a controversial ad featuring a man shoving a club"},
        ])
        self.assertEqual(len(out), 1)

    def test_distinct_stories_survive(self):
        from narrative_desk import dedupe_feed
        out = dedupe_feed([
            {"narrative": "Flock's new AI police tool can track drivers without a license plate"},
            {"narrative": "Marc Lore sells the Timberwolves and Lynx for $4.5 billion"},
            {"narrative": "Jeff Bezos' Blue Origin is building a plant in Hutto, Texas"},
        ])
        self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
