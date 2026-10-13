"""Durable daily journal on an isolated Git branch; contains no addresses/content.

An ambiguous SMTP transaction is never automatically retried. Acceptance is not
claimed to be inbox delivery. The journal also prevents repeated paid AI calls.
"""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BRANCH = "newspaper-delivery-state"

class Journal:
    def __init__(self, day, repository=None, token=None, transport=None):
        self.day = dt.date.fromisoformat(str(day)).isoformat()
        self.repo = repository or os.environ.get("GITHUB_REPOSITORY", "")
        self.token = token or os.environ.get("GH_TOKEN", "")
        self.transport = transport or urlopen
        if not self.repo or not self.token: raise RuntimeError("Delivery journal credentials unavailable")
        self.path = f"receipts/{self.day}.json"
        self.sha, self.state = None, {}

    def api(self, path, method="GET", data=None, missing=False):
        req = Request("https://api.github.com/repos/"+self.repo+"/"+path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Authorization":"Bearer "+self.token,"Accept":"application/vnd.github+json",
                     "Content-Type":"application/json","X-GitHub-Api-Version":"2022-11-28"},method=method)
        try:
            with self.transport(req, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if missing and exc.code == 404: return None
            # No response bodies, tokens, or addresses in error logs.
            raise RuntimeError(f"Journal {method} failed: HTTP {exc.code}") from None

    def read(self):
        obj = self.api("contents/"+self.path+"?ref="+BRANCH, missing=True)
        if obj is None: self.sha, self.state = None, {}
        else:
            self.sha = obj["sha"]
            self.state = json.loads(base64.b64decode(obj["content"]))
            if self.state.get("delivery_date") != self.day: raise RuntimeError("Journal date mismatch")
        return self.state

    def ensure_branch(self):
        if self.api("git/ref/heads/"+BRANCH, missing=True) is None:
            main = self.api("git/ref/heads/main")
            self.api("git/refs", "POST", {"ref":"refs/heads/"+BRANCH,"sha":main["object"]["sha"]})

    def write(self, **changes):
        self.state.update(changes, delivery_date=self.day,
            updated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            run_id=os.environ.get("GITHUB_RUN_ID", "local-test"))
        payload = {"message":f"newspaper receipt {self.day}: {self.state.get('status','prepared')}",
                   "branch":BRANCH,"content":base64.b64encode(json.dumps(self.state,ensure_ascii=False,indent=2).encode()).decode()}
        if self.sha: payload["sha"] = self.sha
        result = self.api("contents/"+self.path, "PUT", payload)
        self.sha = result["content"]["sha"]

    def decision(self):
        state = self.read()
        if state.get("status") == "accepted": return "accepted"
        if state.get("status") in {"sending", "uncertain"}: return "review_required"
        return "send"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--date", default=dt.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat())
    args = parser.parse_args()
    decision = Journal(args.date).decision()
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
            stream.write(f"decision={decision}\ndate={args.date}\n")
    print(f"Daily delivery state: {decision}")
    if decision == "review_required":
        raise RuntimeError("Previous SMTP acceptance is uncertain; inspect before resending")

if __name__ == "__main__": main()
