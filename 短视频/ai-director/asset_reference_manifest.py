#!/usr/bin/env python3
"""Offline private, versioned visual-reference metadata: CineCrew FilmDSL inspired.

Asset-bytes NEVER enter this manifest, logs, prompts, GitHub or CI artifacts.
Caller supplies bytes only transiently in a trusted private runtime. The code
verifies format, pixels and hash, not artistic quality, IP rights, identity, or consent.
Records are source-bound; immutable versions are linked with SHA-256 digests.
No network, local file access, provider calls, automatic image synthesis.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import re
import warnings

import agent_team as team
import film_continuity as film

VERSION="private-visual-reference-manifest-v2"
MAX_IMAGE_BYTES=12*1024*1024
MAX_IMAGE_PIXELS=16*1024*1024
MAX_IMAGE_DIMENSION=8192
IMAGE_FORMATS=frozenset(("image/png","image/jpeg","image/webp"))
SLOTS=frozenset(("identity_front","identity_side","wardrobe",
                 "prop_reference","location_reference"))
KIND_SLOTS={
    "character":frozenset(("identity_front","identity_side","wardrobe")),
    "prop":frozenset(("prop_reference",)),
    "scene":frozenset(("location_reference",)),
}
RECOMMENDED_SLOTS={
    "character":("identity_front","wardrobe"),
    "prop":("prop_reference",),
    "scene":("location_reference",),
}
HEX64=re.compile(r"^[0-9a-f]{64}$")
ID=re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,63}$")


class AssetReferenceError(ValueError):
    """Fixed diagnostic codes only, no user content or local paths."""


def _require(ok, code):
    if not ok:
        raise AssetReferenceError(code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _manifest_entities(plan):
    entries=film.inventory(plan)["entities"]
    return {eid:(kind[:-1] if kind!="props" else "prop")
            for kind,group in entries.items() for eid in group}


def _shot_targets(plan):
    return {s["id"]:{
        entity_id:None for entity_id in (
            s.get("character_ids",[])+s.get("prop_ids",[])+
            ([s["scene_id"]] if s.get("scene_id") is not None else []))}
        for s in plan["shots"]}


def create_empty(plan, source_digest):
    _require(isinstance(source_digest,str) and
             HEX64.fullmatch(source_digest) is not None,
             "ASSET_SOURCE_HASH_REQUIRED")
    targets=_shot_targets(plan)
    return {"version":VERSION,"plan_digest":team.fingerprint(plan),
            "source_digest":source_digest,"cards":{},
            "shot_bindings":targets,
            "shot_slot_bindings":{
                sid:{eid:{} for eid in entities} for sid,entities in targets.items()},
            "human_approved":False,"media_identity_verified":False,
            "usage_rights_verified":False,"reference_bytes_persisted":False,
            "paid_api_authorized":False,
            "private_metadata_only":True}


def _type_check(media_type,data):
    _require(type(media_type) is str and media_type in IMAGE_FORMATS and
             type(data) is bytes and 16<=len(data)<=MAX_IMAGE_BYTES,
             "ASSET_MEDIA_BYTES_INVALID")
    ok=(media_type=="image/png" and data.startswith(b"\x89PNG\r\n\x1a\n")) or (
        media_type=="image/jpeg" and data.startswith(b"\xff\xd8\xff")) or (
        media_type=="image/webp" and data.startswith(b"RIFF") and
        data[8:12]==b"WEBP")
    _require(ok,"ASSET_MEDIA_HEADER_MISMATCH")



def _decoded_image_check(media_type, data):
    """Fully decode single-frame pixels privately; never return bytes or EXIF.

    This is integrity checking, NOT consent, rights or identity verification.
    A missing/unsafe decoder fails closed before registration or verification.
    """
    _type_check(media_type, data)
    try:
        from PIL import Image, ImageFile
    except (ImportError, AttributeError):
        raise AssetReferenceError("ASSET_IMAGE_DECODER_UNAVAILABLE") from None
    _require(not ImageFile.LOAD_TRUNCATED_IMAGES,
             "ASSET_IMAGE_DECODER_UNSAFE_CONFIGURATION")
    expected={"image/png":"PNG", "image/jpeg":"JPEG",
              "image/webp":"WEBP"}[media_type]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data),
                            formats=("PNG", "JPEG", "WEBP")) as image:
                _require(image.format==expected,
                         "ASSET_IMAGE_FORMAT_MISMATCH")
                width,height=image.size
                _require(0<width<=MAX_IMAGE_DIMENSION and
                         0<height<=MAX_IMAGE_DIMENSION and
                         width*height<=MAX_IMAGE_PIXELS,
                         "ASSET_IMAGE_DIMENSIONS_EXCEEDED")
                _require(getattr(image,"n_frames",1)==1,
                         "ASSET_IMAGE_ANIMATED_UNSUPPORTED")
                image.verify()
            # verify() is not proof the pixel stream can be decompressed.
            with Image.open(io.BytesIO(data),
                            formats=("PNG", "JPEG", "WEBP")) as image:
                _require(image.format==expected and image.size==(width,height),
                         "ASSET_IMAGE_FORMAT_MISMATCH")
                _require(getattr(image,"n_frames",1)==1,
                         "ASSET_IMAGE_ANIMATED_UNSUPPORTED")
                image.load()
    except AssetReferenceError:
        raise
    except Exception:
        # Do not leak parser errors containing private metadata.
        raise AssetReferenceError("ASSET_IMAGE_DECODE_INVALID") from None
    return {"width_px":width,"height_px":height,"pixels_decoded":True,"frames":1}

def _card_digest(value):
    return team.fingerprint(value)


def validate(plan, source_digest, manifest):
    """Validate source/immutable revisions/shot version locks; return metadata.

    Does not accept user-supplied truth flags or external URLs/file paths.
    A source plan missing cast remains unverified even if a card exists.
    """
    expected=create_empty(plan,source_digest)
    _require(type(manifest) is dict and
             set(manifest)==set(expected) and
             all(manifest[k]==expected[k] for k in (
                 "version","plan_digest","source_digest","human_approved",
                 "media_identity_verified","usage_rights_verified",
                 "reference_bytes_persisted","paid_api_authorized",
                 "private_metadata_only")) and
             type(manifest.get("cards")) is dict and
             type(manifest.get("shot_bindings")) is dict and
             type(manifest.get("shot_slot_bindings")) is dict,
             "ASSET_MANIFEST_SOURCE_OR_AUTHORITY_INVALID")
    entities=_manifest_entities(plan)
    _require(set(manifest["shot_bindings"])==set(expected["shot_bindings"]) and
             set(manifest["shot_slot_bindings"])==set(expected["shot_slot_bindings"]),
             "ASSET_SHOT_BINDING_COVERAGE")
    cards=manifest["cards"]
    _require(len(cards)<=250 and len(manifest["shot_bindings"])<=1000,
             "ASSET_MANIFEST_SIZE_LIMIT")
    for key,card in cards.items():
        _require(type(key) is str and ID.fullmatch(key) is not None and
                 type(card) is dict and set(card)=={
                     "asset_id","entity_id","entity_kind","slot","versions"} and
                 card["asset_id"]==key and
                 type(card["entity_id"]) is str and
                 card["entity_id"] in entities and
                 card["entity_kind"]==entities[card["entity_id"]] and
                 type(card["slot"]) is str and
                 card["slot"] in KIND_SLOTS[card["entity_kind"]] and
                 type(card["versions"]) is list and
                 0<len(card["versions"])<=16,
                 "ASSET_CARD_INVALID")
        prev=None
        for i,rev in enumerate(card["versions"],1):
            _require(type(rev) is dict and set(rev)=={
                "version","sha256","size_bytes","media_type",
                "previous_revision_digest","rights_status","consent_status",
                "review_status"} and type(rev["version"]) is int and
                rev["version"]==i and type(rev["sha256"]) is str and
                HEX64.fullmatch(rev["sha256"]) is not None and
                type(rev["size_bytes"]) is int and
                16<=rev["size_bytes"]<=MAX_IMAGE_BYTES and
                type(rev["media_type"]) is str and
                rev["media_type"] in IMAGE_FORMATS and
                rev["previous_revision_digest"]==prev and
                rev["rights_status"]=="unverified" and
                rev["consent_status"]=="unverified" and
                rev["review_status"]=="pending",
                "ASSET_REVISION_CHAIN_OR_RIGHTS_INVALID")
            prev=_card_digest(rev)
    missing=[]
    missing_required_slots=[]
    switches=[]
    prev_primary={}
    prev_slot={}
    for sid,target in expected["shot_bindings"].items():
        bindings=manifest["shot_bindings"][sid]
        slot_entities=manifest["shot_slot_bindings"][sid]
        _require(type(bindings) is dict and
                 type(slot_entities) is dict and
                 set(bindings)==set(target) and
                 set(slot_entities)==set(target),
                 "ASSET_SHOT_ENTITY_BINDINGS_INVALID")
        for entity_id,link in bindings.items():
            slots=slot_entities[entity_id]
            _require(type(slots) is dict and
                     set(slots).issubset(KIND_SLOTS[entities[entity_id]]),
                     "ASSET_SHOT_SLOT_BINDINGS_INVALID")
            for slot,ref in slots.items():
                _require(type(ref) is dict and
                         set(ref)=={"asset_id","version","sha256"} and
                         type(ref["asset_id"]) is str and
                         ref["asset_id"] in cards,
                         "ASSET_SHOT_REFERENCE_INVALID")
                card=cards[ref["asset_id"]]
                latest=card["versions"][-1]
                _require(card["entity_id"]==entity_id and card["slot"]==slot
                         and type(ref["version"]) is int
                         and ref["version"]==latest["version"]
                         and ref["sha256"]==latest["sha256"],
                         "ASSET_SHOT_STALE_OR_WRONG_ENTITY")
                current=(ref["asset_id"],ref["version"],ref["sha256"])
                key=(entity_id,slot)
                earlier=prev_slot.get(key)
                if earlier is not None and earlier!=current:
                    switches.append({"entity_id":entity_id,"slot":slot,
                                     "shot_id":sid,
                                     "reason":"slot_version_switch_requires_human_review"})
                prev_slot[key]=current
            for recommended in RECOMMENDED_SLOTS[entities[entity_id]]:
                if recommended not in slots:
                    missing_required_slots.append({
                        "shot_id":sid,"entity_id":entity_id,
                        "slot":recommended,"reason":"recommended_reference_missing"})
            if link is None:
                _require(not slots,"ASSET_PRIMARY_MISSING_WITH_SLOTS")
                missing.append({"shot_id":sid,"entity_id":entity_id,
                                "reason":"reference_not_bound"})
                continue
            _require(type(link) is dict and
                     set(link)=={"asset_id","version","sha256"} and
                     any(link==r for r in slots.values()),
                     "ASSET_PRIMARY_NOT_BOUND_TO_SLOT")
            current=(link["asset_id"],link["version"],link["sha256"])
            earlier=prev_primary.get(entity_id)
            if earlier is not None and earlier!=current:
                switches.append({"entity_id":entity_id,
                                 "slot":"primary","shot_id":sid,
                                 "reason":"reference_switch_requires_human_review"})
            prev_primary[entity_id]=current
    return {
        "kind":VERSION,"manifest_digest":team.fingerprint(manifest),
        "source_digest":source_digest,
        "plan_digest":expected["plan_digest"],
        "cards_count":len(cards),
        "revisions_count":sum(len(x["versions"]) for x in cards.values()),
        "missing_bindings_count":len(missing),
        "missing_bindings":missing,
        "missing_recommended_slot_count":len(missing_required_slots),
        "missing_recommended_slots":missing_required_slots,
        "slot_binding_count":sum(len(assets) for shot in
            manifest["shot_slot_bindings"].values() for assets in shot.values()),
        "reference_switches":switches,
        "per_entity_references_consistent":len(switches)==0,
        "bytes_stored_in_manifest":False,
        "actual_reference_file_exists_verified":False,
        "media_identity_verified":False,
        "usage_rights_verified":False,
        "human_approved":False,
        "ready_to_generate":False,
        "actual_provider_calls":0,
    }


def register_image(plan, source_digest, manifest, *, asset_id, entity_id,
                   slot, image_bytes, media_type):
    """Register next immutable version via trusted private bytes in memory.

    No bytes, path, URL or recognizable image content are retained in output.
    Every registration is a PROPOSAL; license/subject consent remain unverified.
    """
    validate(plan,source_digest,manifest)
    entities=_manifest_entities(plan)
    _require(type(asset_id) is str and ID.fullmatch(asset_id) is not None and
             entity_id in entities and
             slot in KIND_SLOTS[entities[entity_id]],
             "ASSET_ENTITY_OR_SLOT_NOT_AUTHORIZED")
    _decoded_image_check(media_type,image_bytes)
    out=deepcopy(manifest)
    cards=out["cards"]
    if asset_id not in cards:
        cards[asset_id]={"asset_id":asset_id,"entity_id":entity_id,
                         "entity_kind":entities[entity_id],
                         "slot":slot,"versions":[]}
    card=cards[asset_id]
    _require(card["entity_id"]==entity_id and card["slot"]==slot,
             "ASSET_ID_REASSIGNMENT_FORBIDDEN")
    revisions=card["versions"]
    newhash=_sha(image_bytes)
    _require(not revisions or revisions[-1]["sha256"]!=newhash,
             "ASSET_DUPLICATE_REVISION")
    revisions.append({
        "version":len(revisions)+1,"sha256":newhash,
        "size_bytes":len(image_bytes),"media_type":media_type,
        "previous_revision_digest":(
            _card_digest(revisions[-1]) if revisions else None),
        "rights_status":"unverified","consent_status":"unverified",
        "review_status":"pending"})
    # A newer revision MUST invalidate old shots using the same asset; don't
    # silently upgrade them, because appearance may have changed.
    return out


def bind_shot(plan, source_digest, manifest, *, shot_id, entity_id, asset_id):
    """Explicitly select the latest asset revision for a single shot."""
    # Old bindings might intentionally be stale after registration of new
    # version; allow editing them but still require every other field strict.
    out=deepcopy(manifest)
    _require(type(out) is dict and "shot_bindings" in out and
             shot_id in _shot_targets(plan) and
             entity_id in _shot_targets(plan)[shot_id] and
             asset_id in out.get("cards",{}),
             "ASSET_SHOT_BINDING_TARGET_INVALID")
    card=out["cards"][asset_id]
    _require(card["entity_id"]==entity_id and card["versions"],
             "ASSET_SHOT_BINDING_WRONG_ENTITY")
    newest=card["versions"][-1]
    link={"asset_id":asset_id,"version":newest["version"],
          "sha256":newest["sha256"]}
    slots=out["shot_slot_bindings"][shot_id][entity_id]
    primary=out["shot_bindings"][shot_id][entity_id]
    # Adding wardrobe or a side view cannot silently replace the primary
    # face. Rebinding the same primary slot intentionally refreshes its version.
    if primary is None or (type(primary) is dict and
                           primary.get("asset_id") in out["cards"] and
                           out["cards"][primary["asset_id"]]["slot"]==card["slot"]):
        out["shot_bindings"][shot_id][entity_id]=deepcopy(link)
    slots[card["slot"]]=link
    # Reject all malformed fields other than the already-existing stale
    # version bindings; do not allow saving this until all shots are rebound.
    return out


def verify_bytes(manifest, asset_id, version, content_bytes):
    """Private in-memory hash check. This is NOT face/rights/media validation."""
    _require(type(manifest) is dict and
             asset_id in manifest.get("cards",{}),
             "ASSET_VERIFY_UNKNOWN_ASSET")
    revisions=manifest["cards"][asset_id]["versions"]
    _require(type(version) is int and 1<=version<=len(revisions),
             "ASSET_VERIFY_VERSION_INVALID")
    item=revisions[version-1]
    _type_check(item["media_type"],content_bytes)
    _require(len(content_bytes)==item["size_bytes"] and
             _sha(content_bytes)==item["sha256"],
             "ASSET_VERIFY_CONTENT_MISMATCH")
    decoded=_decoded_image_check(item["media_type"],content_bytes)
    return {"asset_id":asset_id,"version":version,
            "sha256_matches":True,"media_header_matches":True,
            "pixels_decoded":decoded["pixels_decoded"],
            "dimensions_px":[decoded["width_px"],decoded["height_px"]],
            "identity_matches_persona":False,
            "rights_verified":False,"human_approved":False,
            "bytes_persisted_by_module":False,"provider_calls":0}
