"""Unit checks for truthful Query deadline calculations."""
import unittest
from datetime import date

from cra_app.issues.deadlines import assess_deadline


class DeadlineTests(unittest.TestCase):
    def test_missing_due_date_never_creates_overdue_days(self):
        result = assess_deadline(
            due_on=None,
            deadline_source=None,
            as_of=date(2026, 10, 31),
        )
        self.assertEqual(result.status, "due_date_unknown")
        self.assertIsNone(result.overdue_days)

    def test_known_due_date_reports_overdue_only_after_boundary(self):
        result = assess_deadline(
            due_on=date(2026, 10, 20),
            deadline_source="Synthetic site SOP",
            as_of=date(2026, 10, 31),
        )
        self.assertEqual(result.status, "overdue")
        self.assertEqual(result.overdue_days, 11)

    def test_reply_resolves_deadline_display(self):
        result = assess_deadline(
            due_on=date(2026, 10, 20),
            deadline_source="Synthetic site SOP",
            as_of=date(2026, 10, 31),
            resolved_on=date(2026, 10, 18),
        )
        self.assertEqual(result.status, "resolved")
        self.assertIsNone(result.overdue_days)


if __name__ == "__main__":
    unittest.main()
