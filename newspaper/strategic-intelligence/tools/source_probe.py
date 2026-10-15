#!/usr/bin/env python3
"""Manual, low-rate source reachability smoke test. NO scheduler, NO publishing.
This probes a URL's metadata and markup; it does NOT verify re-use/AI rights.
Usage:
    python tools/source_probe.py                       # dry-run
    python tools/source_probe.py --execute --limit 10  # actual, consented smoke test
    python tools/source_probe.py --execute --limit 130 --delay 3 --out source_probe_results.json
"""
from __future__ import annotations
import argparse
import json
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

from sync_spec import assert_current

# Operational parameters are generated from the canonical specification.
MAX_BYTES: int
TIMEOUT: int

class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = []
        self.text = []
        self.in_title = False
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        if tag == "title":
            self.in_title = True
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
        if tag == "title":
            self.in_title = False
    def handle_data(self, data):
        v = data.strip()
        if not v or self.skip:
            return
        if self.in_title:
            self.title.append(v)
        else:
            self.text.append(v)

def check(entry, user_agent):
    url = (entry.get("cloud_smoke_20261013", {}).get("verified_access_url")
           or entry.get("recovery_20261013", {}).get("preferred_url")
           or entry["url"])
    result = {"id": entry["id"], "name": entry["name"], "url": url,
              "at": datetime.now(timezone.utc).isoformat(),
              "status": "UNKNOWN", "error": None, "content_type": None,
              "http_status": None, "sample_title": None}
    # SEC asks automated clients to identify their organization and contact.
    if "sec.gov" in url and "@" not in user_agent:
        result["status"] = "SKIPPED_REQUIRES_CONTACT_IN_USER_AGENT"
        return result
    if not url.startswith("https://"):
        result["status"] = "SKIPPED_NOT_HTTPS"
        return result
    req = Request(url, headers={"User-Agent": user_agent,
                                "Accept": "text/html,application/json,application/rss+xml,application/atom+xml,application/xml,text/xml,*/*"})
    try:
        with urlopen(req, timeout=TIMEOUT) as response:
            result["http_status"] = response.status
            ctype = response.headers.get("Content-Type", "").lower()
            result["content_type"] = ctype
            data = response.read(MAX_BYTES + 1)
            result["truncated"] = len(data) > MAX_BYTES
            data = data[:MAX_BYTES]
            decoded = data.decode("utf-8", errors="replace")
            if "json" in ctype:
                obj = json.loads(decoded)
                result["record_count"] = 0
                if isinstance(obj, list):
                    result["record_count"] = len(obj)
                    result["sample_title"] = "JSON array, length " + str(len(obj))
                elif isinstance(obj, dict):
                    nested = obj.get("data")
                    if isinstance(nested, list):
                        result["record_count"] = len(nested)
                    elif isinstance(nested, dict):
                        result["record_count"] = sum(len(v) for v in nested.values() if isinstance(v, list))
                    elif isinstance(obj.get("studies"), list):
                        result["record_count"] = len(obj["studies"])
                    elif isinstance(obj.get("resultList"), dict):
                        result["record_count"] = len(obj["resultList"].get("result", []))
                    result["sample_title"] = ", ".join(list(obj)[:5])
                result["status"] = "JSON_HAS_RECORDS" if result["record_count"] else "JSON_NO_RECORDS"
            elif any(v in ctype for v in ("rss", "xml", "atom")) or decoded.lstrip().startswith("<?xml"):
                try:
                    tree = ElementTree.fromstring(data)
                    rss = tree.findall(".//item")
                    atom = tree.findall(".//{http://www.w3.org/2005/Atom}entry")
                    rdf = tree.findall(".//{http://purl.org/rss/1.0/}item")
                    pubmed = tree.findall(".//IdList/Id") if tree.tag.lower().endswith("esearchresult") else []
                    result["record_count"] = len(rss) + len(atom) + len(rdf) + len(pubmed)
                    title = tree.find(".//item/title")
                    if title is None:
                        title = tree.find(".//{http://www.w3.org/2005/Atom}entry/{http://www.w3.org/2005/Atom}title")
                    if title is None:
                        title = tree.find(".//{http://purl.org/rss/1.0/}item/{http://purl.org/rss/1.0/}title")
                    result["sample_title"] = title.text[:200] if title is not None and title.text else (pubmed[0].text if pubmed else None)
                    result["status"] = "XML_PARSED_HAS_ENTRIES" if result["record_count"] else "XML_PARSED_NO_ENTRIES"
                except ElementTree.ParseError as ex:
                    result["status"] = "XML_TRUNCATED_OR_INVALID"
                    result["error"] = str(ex)[:250]
            elif "html" in ctype:
                parser = PageText()
                parser.feed(decoded)
                result["sample_title"] = " ".join(parser.title)[:200]
                result["approx_text_chars"] = len(" ".join(parser.text))
                result["status"] = "HTML_HAS_TEXT" if result["approx_text_chars"] > 400 else "HTML_THIN_OR_DYNAMIC"
            else:
                result["status"] = "OTHER_CONTENT_TYPE"
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        result["status"] = "REQUEST_FAILED"
        result["http_status"] = getattr(exc, "code", None)
        result["error"] = str(exc)[:350]
    return result

def main():
    global MAX_BYTES, TIMEOUT
    root = Path(__file__).resolve().parents[1]
    try:
        config = assert_current(root)["source_probe"]
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit("Specification preflight failed: " + str(exc))
    MAX_BYTES = config["max_bytes"]
    TIMEOUT = config["timeout_seconds"]
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true", help="Make real HTTPS requests")
    p.add_argument("--limit", type=int, default=config["default_limit"])
    p.add_argument("--delay", type=float, default=config["default_delay_seconds"], help="Seconds between sources; minimum from canonical contract")
    p.add_argument("--out", default=str(root / config["default_output"]))
    p.add_argument("--user-agent", default="StrategicIntelligenceSourceAudit/0.1 (noncommercial-research; contact-required-for-SEC)")
    args = p.parse_args()
    if not (config["minimum_delay_seconds"] <= args.delay < float("inf")):
        p.error("Delay is below the canonical minimum or is not finite")
    if args.execute and Path(args.out).exists():
        p.error("Refusing to overwrite an existing audit; choose a new --out path")
    registry = Path(__file__).resolve().parents[1] / "SOURCE_REGISTRY.json"
    entries = json.loads(registry.read_text(encoding="utf-8"))["entries"][:max(0, args.limit)]
    if not args.execute:
        print("DRY RUN: would check", len(entries), "URLs. Pass --execute to make network requests.")
        return
    results = []
    for n, entry in enumerate(entries):
        if n:
            time.sleep(args.delay)
        r = check(entry, args.user_agent)
        results.append(r)
        print(entry["id"], r["status"], r["http_status"] or "", flush=True)
    Path(args.out).write_text(json.dumps({"executed_at": datetime.now(timezone.utc).isoformat(),
                                         "warnings": ["This does not establish content licensing, AI use rights or long-term reliability."],
                                         "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Results:", args.out)
if __name__ == "__main__":
    main()

