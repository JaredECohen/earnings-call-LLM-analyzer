"""`_looks_like_label` decides which sections get re-asked. Its two period
patterns were dead until 2026-09-19 (``r"\\d"`` in a raw string is a literal
backslash), masked by the ≤3-word rule; these pin the intended behaviour."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ANTHROPIC_API_KEY", "offline-test-key")

import app as app_module  # noqa: E402


class LooksLikeLabelTest(unittest.TestCase):
    def test_period_labels_and_placeholders_are_labels(self):
        for value in (
            "2026Q1", "2025q4", " 2026Q1 ",
            "FY2026 Q1 (2026Q1)", "fy2026q1(2026q1)",
            "Not provided", "N/A", "", "   ",
            "Strong quarter overall",  # three words: still a label by the length rule
        ):
            self.assertTrue(app_module._looks_like_label(value), value)

    def test_real_content_is_not_a_label(self):
        for value in (
            "Revenue grew 12% year over year, driven by Azure and Copilot adoption.",
            "FY2026 Q1 revenue of $70B was up 15%; guidance raised for the next quarter.",
        ):
            self.assertFalse(app_module._looks_like_label(value), value)

    def test_period_patterns_match_on_their_own(self):
        # The fixed patterns must carry the check even without the word-count rule.
        self.assertIsNotNone(app_module._QUARTER_LABEL_RE.fullmatch("2026q1"))
        self.assertIsNotNone(app_module._FISCAL_QUARTER_LABEL_RE.fullmatch("fy2026 q1 (2026q1)"))
        self.assertIsNone(app_module._QUARTER_LABEL_RE.fullmatch("2026q5"))
        self.assertIsNone(app_module._QUARTER_LABEL_RE.fullmatch(r"\d{4}q1"))

    def test_non_strings_are_not_labels(self):
        self.assertFalse(app_module._looks_like_label(None))
        self.assertFalse(app_module._looks_like_label(42))


if __name__ == "__main__":
    unittest.main()
