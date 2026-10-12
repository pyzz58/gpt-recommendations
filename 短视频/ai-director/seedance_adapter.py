"""Single-shot official Seedance API bridge. Never called on import or by CI.

prepare_shot is offline. submit_once/query_once/download_result are real HTTPS
operations for a future authorized private runtime; no automatic retries,
environment-key discovery, CLI dispatch, batch loop, or publishing.
Approval arguments describe an external operator decision, NOT authentication
or a provider-enforced spending cap. See SEEDANCE_API_AUDIT.md.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import tempfile
from urllib.parse import urlsplit

import director_v2
import director_workbook
from private_result_checkpoint import _atomic_create, _secure_dir, _fsync_folder

PROVIDERS = {
    "volcengine": ("ark.cn-beijing.volces.com", "doubao-seedance-2-5-260628",
                   ".tos-cn-beijing.volces.com"),
    "byteplus": ("ark.ap-southeast.bytepluses.com", "dreamina-seedance-2-5-260628",
                 ".tos-ap-southeast-1.volces.com"),
}
TASK_PATH = "/api/v3/contents/generations/tasks"
TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,200}\Z")
MAX_JSON = 2 * 1024 * 1024
MAX_VIDEO = 256 * 1024 * 1024


class SeedanceError(ValueError):
    """Static error codes; never reveal keys, prompts or signed URLs."""


def _require(ok, code):
    if not ok:
        raise SeedanceError(code)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def prepare_shot(base, direction, shot_id, *, provider, audio_mode="silent_post",
                 reference_images=()):
    """Offline exact request proposal; a deliberately small 4..15s/720p subset.

Reference images are reviewed HTTPS URLs, role=reference_image, max three in
this adapter. No uploading/first-last-frame/video/audio references yet.
Absent references produce a technical probe, not identity-consistent footage.
"""
    _require(provider in PROVIDERS, "PROVIDER_NOT_SUPPORTED")
    _require(audio_mode in ("silent_post", "native_dialogue"), "AUDIO_MODE_INVALID")
    book = director_workbook.compile_workbook(base, direction)
    _require(book["director_review"]["production_blueprint_ready"], "DIRECTOR_BLUEPRINT_INCOMPLETE")
    package = director_v2.compile_package(base, direction)
    jobs = [x for x in package["shots"] if x["shot_id"] == shot_id]
    _require(len(jobs) == 1, "SHOT_NOT_FOUND")
    job = jobs[0]; d = job["direction"]; duration = job["duration"]
    _require(job["execution_route"] == "ai_video", "POST_SHOT_NOT_DISPATCHABLE")
    _require(type(duration) in (int, float) and float(duration).is_integer()
             and 4 <= duration <= 15, "ADAPTER_DURATION_OUTSIDE_REVIEWED_SUBSET")
    _require((d.get("shootability") or {}).get("mode") == "single_take",
             "SPLIT_SHOT_REQUIRES_SEGMENT_ADAPTATION")
    prompt = job["prompts"]["seedance"]
    speech = deepcopy(d["speech"])
    if audio_mode == "native_dialogue":
        _require(not speech["voiceover"]["text"], "NATIVE_VO_NOT_ADAPTED")
        _require(bool(speech["dialogue"]), "NATIVE_DIALOGUE_MISSING")
        for line in speech["dialogue"]:
            _require(line.get("kind") in ("onscreen_dialogue", "offscreen_dialogue"),
                     "EXPLICIT_DIALOGUE_KIND_REQUIRED")
        prompt = prompt.replace("Voiceover, sound effects, music and exact charts are handled in post-production.",
                                "Generate the authored dialogue and scene audio below; subtitles and charts remain post-production.")
        prompt += "\nExact dialogue contract (local seconds, only the named speaker speaks): " + json.dumps(speech, ensure_ascii=False)
        prompt += "\nDo not speak stage directions. Offscreen speakers must not animate a visible listener's mouth."
    content = [{"type": "text", "text": prompt}]
    _require(type(reference_images) in (list, tuple) and len(reference_images) <= 3,
             "REFERENCE_COUNT_OUTSIDE_REVIEWED_SUBSET")
    for url in reference_images:
        _require(isinstance(url, str), "REFERENCE_URL_INVALID")
        parsed = urlsplit(url)
        _require(parsed.scheme == "https" and parsed.hostname and not parsed.username
                 and not parsed.password and not parsed.fragment, "REFERENCE_URL_INVALID")
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
    packet = {
        "version": "seedance-single-shot-v1", "provider": provider, "shot_id": shot_id,
        "base_digest": digest(base), "direction_digest": digest(direction),
        "body": {"model": PROVIDERS[provider][1], "content": content,
                 "ratio": base["aspect_ratio"], "duration": int(duration),
                 "resolution": "720p", "generate_audio": audio_mode == "native_dialogue",
                 "watermark": True},
        "audio_mode": audio_mode, "postproduction": deepcopy(job["postproduction_job"]),
        "scope": "reference_guided_candidate" if reference_images else "reference_free_technical_probe",
        "warnings": ["No real media test or human approval", "Quoted cost is not a provider spending guarantee",
                     "Native audio must be checked against postproduction speech; do not duplicate voices"],
        "human_approved": False, "media_generated": False,
    }
    packet["request_digest"] = digest(packet)
    return packet


def _packet(packet):
    _require(isinstance(packet, dict), "PACKET_INVALID")
    copy = deepcopy(packet); claimed = copy.pop("request_digest", None)
    _require(claimed == digest(copy) and copy.get("provider") in PROVIDERS
             and copy.get("version") == "seedance-single-shot-v1", "PACKET_CHANGED")
    _require(copy["body"].get("model") == PROVIDERS[copy["provider"]][1], "MODEL_CHANGED")
    body = copy["body"]
    _require(set(body) == {"model", "content", "ratio", "duration", "resolution", "generate_audio", "watermark"}
             and body["ratio"] == "9:16" and body["resolution"] == "720p"
             and type(body["duration"]) is int and 4 <= body["duration"] <= 15
             and body["watermark"] is True
             and copy.get("audio_mode") in ("silent_post", "native_dialogue")
             and body["generate_audio"] is (copy["audio_mode"] == "native_dialogue"),
             "REQUEST_OUTSIDE_REVIEWED_SUBSET")
    content = body["content"]
    _require(isinstance(content, list) and 1 <= len(content) <= 4
             and isinstance(content[0], dict) and set(content[0]) == {"type", "text"}
             and content[0]["type"] == "text" and isinstance(content[0]["text"], str)
             and bool(content[0]["text"].strip()), "CONTENT_INVALID")
    for item in content[1:]:
        _require(isinstance(item, dict) and set(item) == {"type", "image_url", "role"}
                 and item["type"] == "image_url" and item["role"] == "reference_image"
                 and isinstance(item["image_url"], dict)
                 and set(item["image_url"]) == {"url"}
                 and isinstance(item["image_url"]["url"], str), "REFERENCE_URL_INVALID")
        url = urlsplit(item["image_url"]["url"])
        _require(url.scheme == "https" and url.hostname and not url.username
                 and not url.password and not url.fragment, "REFERENCE_URL_INVALID")
    return claimed


def _private_root(path):
    path = Path(path)
    for p in (path, *path.parents):
        _require(not p.is_symlink() and not (p / ".git").exists(), "PRIVATE_STORAGE_REQUIRED")
    _secure_dir(path)
    _require(path.stat().st_uid == os.geteuid(), "PRIVATE_STORAGE_OWNER")
    return path


def _read(path):
    _require(not path.is_symlink() and path.is_file() and path.stat().st_size <= MAX_JSON
             and not (path.stat().st_mode & 0o077), "PRIVATE_RECORD_INVALID")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _request(provider, method, path, key, body=None):
    _require(provider in PROVIDERS and isinstance(key, str) and key and
             not any(c.isspace() for c in key), "API_CONFIGURATION_INVALID")
    conn = http.client.HTTPSConnection(PROVIDERS[provider][0], timeout=60,
                                      context=ssl.create_default_context())
    try:
        conn.request(method, path, body=None if body is None else json.dumps(body).encode(),
                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        response = conn.getresponse()
        _require(200 <= response.status < 300, "API_HTTP_FAILURE_NO_AUTOMATIC_RETRY")
        raw = response.read(MAX_JSON + 1)
        _require(len(raw) <= MAX_JSON, "API_RESPONSE_TOO_LARGE")
        data = json.loads(raw)
        _require(isinstance(data, dict), "API_RESPONSE_INVALID")
        return data
    except SeedanceError:
        raise
    except Exception:
        raise SeedanceError("API_RESULT_UNKNOWN_NO_AUTOMATIC_RETRY") from None
    finally:
        conn.close()


def submit_once(packet, *, private_dir, api_key, approval):
    """ONE paid POST after external authorization of this exact proposal.

Caller supplies approval {request_digest, quoted_cost, max_cost, currency,
rights_reviewed}. Amounts are operator-supplied estimates; actual bill may
differ. Account-level limits and genuine user consent remain runtime duties.
Any intent (including uncertain POST) prevents resubmission in this directory.
"""
    sha = _packet(packet); root = _private_root(private_dir)
    _require(isinstance(approval, dict) and approval.get("request_digest") == sha
             and approval.get("rights_reviewed") is True
             and approval.get("currency") == ("CNY" if packet["provider"] == "volcengine" else "USD"),
             "EXACT_OPERATOR_APPROVAL_REQUIRED")
    try:
        quoted = Decimal(str(approval["quoted_cost"])); ceiling = Decimal(str(approval["max_cost"]))
        _require(quoted.is_finite() and ceiling.is_finite() and 0 < quoted <= ceiling,
                 "COST_REVIEW_INVALID")
    except (KeyError, InvalidOperation):
        raise SeedanceError("COST_REVIEW_INVALID") from None
    _require(not (root / "intent.json").exists(), "SUBMISSION_ALREADY_ATTEMPTED_RECONCILE")
    # Shared existing immutable fsync helper; no new generic journal framework.
    _atomic_create(root / "intent.json", {"packet": packet, "approval": approval})
    reply = _request(packet["provider"], "POST", TASK_PATH, api_key, packet["body"])
    task_id = reply.get("id")
    _require(isinstance(task_id, str) and TASK_ID.fullmatch(task_id), "TASK_ID_MISSING_RECONCILE")
    receipt = {"task_id": task_id, "request_digest": sha, "provider": packet["provider"]}
    _atomic_create(root / "receipt.json", receipt)
    return receipt


def query_once(*, private_dir, api_key):
    """One GET for a saved task. Caller may query again; never re-POST here."""
    root = _private_root(private_dir); receipt = _read(root / "receipt.json")
    intent = _read(root / "intent.json"); packet = intent["packet"]
    _require(receipt.get("request_digest") == _packet(packet)
             and receipt.get("provider") == packet["provider"], "RECEIPT_MISMATCH")
    task_id = receipt.get("task_id")
    _require(isinstance(task_id, str) and TASK_ID.fullmatch(task_id), "TASK_ID_INVALID")
    result = _request(receipt["provider"], "GET", TASK_PATH + "/" + task_id, api_key)
    _require(result.get("id") == task_id and result.get("status") in
             ("queued", "running", "succeeded", "failed", "cancelled", "expired"), "TASK_RESPONSE_MISMATCH")
    if result["status"] == "succeeded":
        _require(result.get("model") == packet["body"]["model"], "RESULT_MODEL_MISMATCH")
        _require(isinstance(result.get("content"), dict) and
                 isinstance(result["content"].get("video_url"), str), "RESULT_URL_MISSING")
        if not (root / "result.json").exists():
            _atomic_create(root / "result.json", result)
    # Caller may read signed URL from private storage, never print it in public logs.
    return {"task_id": task_id, "status": result["status"],
            "provider_generation_succeeded": result["status"] == "succeeded",
            "locally_saved": (root / "video.mp4").is_file(), "human_approved": False}


def download_result(*, private_dir):
    """Save provider bytes privately. No API key is sent to the media host.

Container signature/size are checked only; full decode, timing, audio, identity
and artistic review are separate and remain unverified.
"""
    root = _private_root(private_dir); receipt = _read(root / "receipt.json")
    intent = _read(root / "intent.json"); packet = intent["packet"]
    _require(receipt.get("request_digest") == _packet(packet)
             and receipt.get("provider") == packet["provider"], "RECEIPT_MISMATCH")
    result = _read(root / "result.json")
    _require(result.get("status") == "succeeded" and result.get("id") == receipt["task_id"],
             "RESULT_NOT_SUCCEEDED")
    _require(result.get("model") == packet["body"]["model"], "RESULT_MODEL_MISMATCH")
    url = urlsplit(result["content"]["video_url"])
    _require(url.scheme == "https" and url.hostname and
             url.hostname.endswith(PROVIDERS[receipt["provider"]][2]) and
             url.port in (None, 443) and not url.username and not url.password and not url.fragment,
             "MEDIA_HOST_NOT_REVIEWED")
    _require(not (root / "video.mp4").exists(), "MEDIA_ALREADY_SAVED")
    conn = http.client.HTTPSConnection(url.hostname, timeout=60, context=ssl.create_default_context())
    fd, temp = tempfile.mkstemp(prefix=".video-", dir=root)
    try:
        conn.request("GET", url.path + ("?" + url.query if url.query else ""))
        response = conn.getresponse()
        _require(response.status == 200, "MEDIA_DOWNLOAD_FAILED_NO_REDIRECT")
        declared = response.getheader("Content-Length")
        if declared is not None:
            _require(declared.isdigit() and 12 <= int(declared) <= MAX_VIDEO, "MEDIA_LENGTH_INVALID")
        total = 0; sha = hashlib.sha256(); prefix = b""
        with os.fdopen(fd, "wb") as f:
            fd = None
            while True:
                chunk = response.read(65536)
                if not chunk: break
                total += len(chunk); _require(total <= MAX_VIDEO, "MEDIA_TOO_LARGE")
                if len(prefix) < 12: prefix = (prefix + chunk)[:12]
                sha.update(chunk); f.write(chunk)
            _require(total >= 12 and prefix[4:8] == b"ftyp", "MEDIA_CONTAINER_INVALID")
            _require(declared is None or total == int(declared), "MEDIA_TRUNCATED")
            f.flush(); os.fsync(f.fileno())
        os.link(temp, root / "video.mp4"); _fsync_folder(root)
        info = {"task_id": receipt["task_id"], "request_digest": receipt["request_digest"],
                "sha256": sha.hexdigest(), "bytes": total, "container_signature_checked": True,
                "fully_decoded": False, "human_approved": False, "final_film_completed": False}
        _atomic_create(root / "media.json", info)
        return info
    except SeedanceError:
        raise
    except Exception:
        raise SeedanceError("MEDIA_SAVE_INCOMPLETE_RECONCILE") from None
    finally:
        conn.close()
        if fd is not None: os.close(fd)
        if os.path.exists(temp): os.unlink(temp)
