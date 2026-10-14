"""Credential isolation: preview/prepare never see SMTP secrets."""
from pathlib import Path
import unittest


class MailSecretsSafetyTests(unittest.TestCase):
    def setUp(self):
        self.workflow=(Path(__file__).resolve().parent.parent/
                       ".github/workflows/newspaper.yml").read_text(encoding="utf-8")

    def test_smtp_credentials_only_in_send_step(self):
        prefix, tail=self.workflow.split("      - name: Send prebuilt edition via SMTP",1)
        for value in ("secrets.NEWSPAPER_SMTP_PASSWORD","secrets.NEWSPAPER_SMTP_FROM","secrets.NEWSPAPER_TO"):
            self.assertNotIn(value,prefix)
            self.assertIn(value,tail)
        send=tail.split("      - name: Make accepted-mail receipt",1)[0]
        self.assertIn("github.ref == 'refs/heads/main'",send)
        self.assertIn("steps.phase.outputs.phase == 'send'",send)
        self.assertIn("prepared_delivery.py",send)
        self.assertNotIn("digest.py",send)

    def test_preview_and_pr_do_not_use_credentials(self):
        w=self.workflow
        preview=w.split("      - name: Preview without SMTP or LLM credentials",1)[1].split(
            "      - name: Live-source PDF integration",1)[0]
        self.assertIn("--demo",preview)
        self.assertIn("--dry-run",preview)
        self.assertNotIn("secrets.",preview)
        self.assertIn("inputs.preview_kind",w)
        self.assertIn("github.event_name == 'pull_request'",w)


if __name__=="__main__":
    unittest.main()
