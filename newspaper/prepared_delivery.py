"""Newspaper V2: immutable prebuilt edition bundle and SMTP handoff.

This module uses only Python's standard library so the scheduled send stage
does not need RSS, AI, spaCy, translation, PDF rendering, or network scraping.
A successful SMTP handoff is NOT a confirmed inbox delivery.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.message
import hashlib
import json
import os
from pathlib import Path
import re
import smtplib
import ssl
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")
BUNDLE_SCHEMA = 2
FILES = ("edition.pdf", "mail.html", "mail.txt")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assert_delivery_window(now: dt.datetime, edition: dt.date) -> None:
    """Only send today's already prepared edition from 07:00 to 07:59 BJT."""
    if not isinstance(now, dt.datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Delivery requires an aware clock")
    local = now.astimezone(BEIJING)
    begin = dt.datetime.combine(edition, dt.time(7, 0), tzinfo=BEIJING)
    if not begin <= local < begin + dt.timedelta(hours=1):
        raise RuntimeError("Outside today's authorized Beijing 07:00-08:00 send window")


def write_bundle(directory: Path, edition: dt.date, subject: str,
                 html_body: str, text_body: str, pdf_path: Path) -> Path:
    directory = Path(directory)
    if not isinstance(edition, dt.date) or not re.fullmatch(r"全球新闻选编｜\d{4}-\d{2}-\d{2} 06:00截稿", subject):
        raise ValueError("Invalid production edition / subject")
    if str(edition) not in subject:
        raise ValueError("Subject date and edition differ")
    if len(html_body.strip()) < 50 or len(text_body.strip()) < 20:
        raise ValueError("Refuse to prepare an empty or placeholder email")
    pdf_bytes = Path(pdf_path).read_bytes()
    if not pdf_bytes.startswith(b"%PDF-") or len(pdf_bytes) < 100:
        raise ValueError("Refuse to prepare a missing or invalid PDF")
    directory.mkdir(parents=True, exist_ok=True)
    payloads = {
        "edition.pdf": pdf_bytes,
        "mail.html": html_body.encode("utf-8"),
        "mail.txt": text_body.encode("utf-8"),
    }
    for filename, payload in payloads.items():
        (directory / filename).write_bytes(payload)
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "edition_date": edition.isoformat(),
        "cutoff_bjt": "06:00",
        "subject": subject,
        "sha256": {name: sha256(payload) for name, payload in payloads.items()},
    }
    staged = directory / "manifest.json.tmp"
    staged.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    staged.replace(directory / "manifest.json")  # last: means bundle is complete
    return directory / "manifest.json"


def read_bundle(directory: Path, edition: dt.date):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != BUNDLE_SCHEMA or manifest.get("edition_date") != edition.isoformat():
        raise ValueError("Edition mismatch or unsupported bundle schema")
    if manifest.get("cutoff_bjt") != "06:00":
        raise ValueError("Unexpected cutoff in prepared bundle")
    subject = manifest.get("subject", "")
    if subject != f"全球新闻选编｜{edition.isoformat()} 06:00截稿":
        raise ValueError("Prepared subject does not match the edition")
    payloads = {}
    if set(manifest.get("sha256", {})) != set(FILES):
        raise ValueError("Unexpected prepared file inventory")
    for name in FILES:
        payload = (directory / name).read_bytes()
        if sha256(payload) != manifest["sha256"][name]:
            raise ValueError("Prepared edition hash mismatch: " + name)
        payloads[name] = payload
    if not payloads["edition.pdf"].startswith(b"%PDF-"):
        raise ValueError("Prepared PDF invalid")
    return subject, payloads


def send_bundle(directory: Path, edition: dt.date, *, now: dt.datetime | None = None,
                smtp_factory=None):
    assert_delivery_window(now or dt.datetime.now(BEIJING), edition)
    subject, files = read_bundle(directory, edition)
    sender = os.environ.get("SMTP_FROM", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    recipient = os.environ.get("NEWSPAPER_TO", "").strip()
    if not sender or not password or not recipient:
        raise RuntimeError("Newspaper SMTP secrets not configured")
    if any(ch in (sender + recipient) for ch in "\r\n"):
        raise ValueError("Invalid email header")
    msg = email.message.EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    digest = sha256(files["edition.pdf"])[:24]
    domain = sender.rpartition("@")[2]
    if not domain or not re.fullmatch(r"[A-Za-z0-9.-]+", domain):
        raise ValueError("Invalid SMTP sender domain")
    msg["Message-ID"] = f"<newspaper-{edition:%Y%m%d}-{digest}@{domain}>"
    msg.set_content(files["mail.txt"].decode("utf-8"))
    msg.add_alternative(files["mail.html"].decode("utf-8"), subtype="html")
    msg.add_attachment(files["edition.pdf"], maintype="application", subtype="pdf",
                       filename=f"global-briefing-{edition.isoformat()}.pdf")
    with (smtp_factory or smtplib.SMTP_SSL)(
        os.environ.get("SMTP_HOST", "smtp.qq.com"),
        int(os.environ.get("SMTP_PORT", "465")),
        timeout=30, context=ssl.create_default_context(),
    ) as smtp:
        smtp.login(sender, password)
        refusals = smtp.send_message(msg)
    if refusals:
        raise RuntimeError("SMTP refused one or more recipients")
    # Message-ID is client supplied and does not certify inbox delivery.
    print(f"NEWSPAPER_SMTP_ACCEPTED edition={edition.isoformat()} message_id={msg['Message-ID']}")
    return msg["Message-ID"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-dir", required=True)
    parser.add_argument("--edition-date", required=True, help="YYYY-MM-DD in Beijing")
    args = parser.parse_args()
    send_bundle(Path(args.bundle_dir), dt.date.fromisoformat(args.edition_date))


if __name__ == "__main__":
    main()
