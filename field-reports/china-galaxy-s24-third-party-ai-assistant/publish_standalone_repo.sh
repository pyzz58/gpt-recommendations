#!/usr/bin/env bash
# Publish a self-contained public report repository using an authenticated GitHub CLI.
# Execute only after reviewing the public README and confirming the GitHub account.
set -euo pipefail

command -v gh >/dev/null || { echo "GitHub CLI (gh) is required."; exit 1; }
command -v git >/dev/null || { echo "git is required."; exit 1; }
gh auth status >/dev/null

OWNER="$(gh api user --jq .login)"
ACCOUNT_ID="$(gh api user --jq .id)"
EXPECTED_OWNER="pyzz58"
NAME="galaxy-s24-china-ai-assistant-experiment"

if [[ "$OWNER" != "$EXPECTED_OWNER" ]]; then
  echo "Connected GitHub account ($OWNER) differs from expected public account ($EXPECTED_OWNER); stopping."
  exit 1
fi

if gh repo view "$OWNER/$NAME" --json name >/dev/null 2>&1; then
  echo "Repository $OWNER/$NAME already exists. Review manually; no overwrite performed."
  exit 1
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
git clone --depth 1 "https://github.com/$OWNER/gpt-recommendations.git" "$WORK_DIR/source"
mkdir -p "$WORK_DIR/new-repo/.github/ISSUE_TEMPLATE"
cp "$WORK_DIR/source/field-reports/china-galaxy-s24-third-party-ai-assistant/README.md" "$WORK_DIR/new-repo/README.md"

cat > "$WORK_DIR/new-repo/.github/ISSUE_TEMPLATE/device-report.md" <<'TEMPLATE'
---
name: Device reproduction report
about: Report a Samsung model/firmware on which you tested the assistant side-key behavior
title: "[Device] "
---

Please share only technical details you are comfortable making public.

**Model (e.g. SM-S9210):**

**Android / One UI version:**

**Firmware region / CSC (optional):**

**Original side-key behavior:** (record whether behavior 101, 5, or something else was observed)

**Assistant mechanism tested:** (VoiceInteractionService, ACTION_ASSIST Activity, or other)

**Result and minimal sanitized logs:**

**Reboot persistence tested?** (yes / no)

Do **not** paste IMEI, serial number, Android ID, phone number, location, account name, device screenshots containing personal data, API keys, or full logcat dumps.
TEMPLATE

cd "$WORK_DIR/new-repo"
git init -b main
git add README.md .github/ISSUE_TEMPLATE/device-report.md
git -c user.name="Independent Android Device Research" \
    -c user.email="$ACCOUNT_ID+$OWNER@users.noreply.github.com" \
    commit -m "docs: publish privacy-safe Galaxy S24 assistant experiment"

gh repo create "$OWNER/$NAME" \
  --public \
  --source=. \
  --remote=origin \
  --push \
  --description="Real-device Galaxy S24 CHC / One UI 8.5 experiment: side-key 101 vs 5, failed voice session, working ACTION_ASSIST, and STT limitations."

gh repo edit "$OWNER/$NAME" \
  --add-topic "samsung,galaxy-s24,one-ui,android-16,android-assistant,bixby,action-assist,adb"

echo "Published https://github.com/$OWNER/$NAME"
