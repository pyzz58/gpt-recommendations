"""Credential-boundary regression for the public Newspaper workflow."""
from pathlib import Path
import unittest

class MailSecretsSafetyTests(unittest.TestCase):
    def test_secrets_only_enter_default_branch_send_step(self):
        path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "newspaper.yml"
        workflow = path.read_text(encoding="utf8")
        prefix, send = workflow.split("      - name: Send real daily report", 1)
        self.assertNotIn("secrets.NEWSPAPER_SMTP_PASSWORD", prefix)
        self.assertNotIn("secrets.NEWSPAPER_SMTP_FROM", prefix)
        self.assertNotIn("secrets.NEWSPAPER_TO", prefix)
        self.assertIn("github.ref == 'refs/heads/main'", send)
        self.assertIn("github.event_name == 'schedule'", send)
        self.assertIn("secrets.NEWSPAPER_SMTP_PASSWORD", send)
        self.assertIn("python newspaper/digest.py", send)
    def test_preview_without_secrets(self):
        path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "newspaper.yml"
        w = path.read_text(encoding="utf8")
        preview = w.split("      - name: Preview only",1)[1].split("      - name: Send real daily report",1)[0]
        self.assertIn("python newspaper/digest.py --demo", preview)
        self.assertNotIn("secrets.", preview)
if __name__ == "__main__":
    unittest.main()
