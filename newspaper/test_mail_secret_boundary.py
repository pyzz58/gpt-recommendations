"""No mail secrets in PR/preview/prepare; only explicit send on main."""
from pathlib import Path
import unittest


class MailSecretsSafetyTests(unittest.TestCase):
    def setUp(self):
        self.workflow=(Path(__file__).resolve().parent.parent/
                       ".github/workflows/newspaper.yml").read_text(encoding="utf-8")

    def test_smtp_only_after_daily_sent_receipt_check_and_main_send_guard(self):
        w=self.workflow
        receipt=w.index("      - name: Check sent receipt (never means inbox delivery)")
        config=w.index("      - name: Check QQ SMTP configuration")
        sending=w.index("      - name: Send verified edition via QQ SMTP")
        self.assertLess(receipt,config)
        self.assertLess(config,sending)
        config_segment=w[config:w.index("      - name: Restore prebuilt verified edition")]
        send_segment=w[sending:w.index("      - name: Make accepted-mail receipt")]
        for secret in ("secrets.NEWSPAPER_SMTP_PASSWORD","secrets.NEWSPAPER_SMTP_FROM",
                       "secrets.NEWSPAPER_TO"):
            self.assertNotIn(secret,w[:receipt])
            self.assertIn(secret,config_segment)
            self.assertIn(secret,send_segment)
        self.assertIn("steps.receipt.outputs.cache-hit != 'true'",config_segment)
        self.assertIn("steps.phase.outputs.phase == 'send'",config_segment)
        self.assertIn("github.ref == 'refs/heads/main'",config_segment)
        self.assertIn("steps.phase.outputs.phase == 'send'",send_segment)
        self.assertIn("github.ref == 'refs/heads/main'",send_segment)
        self.assertIn("prepared_delivery.py",send_segment)

    def test_preview_and_pr_are_credential_free(self):
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
