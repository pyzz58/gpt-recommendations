# CRA authorized trial record

状态：BLOCKED

Date: 2026-11-07.

## Current conclusion

No authorized real-data trial has been performed. The repository contains a
deployment candidate and synthetic verification only. It must not be described
as authorized-trial ready, clinically validated or production deployed.

## Required approvals and environment

| Prerequisite | Current state | Required evidence |
| --- | --- | --- |
| Approved use and accountable owner | Missing | Written use scope, owner and review date |
| Approved OIDC identity provider | Missing | Successful login with actor/tenant claims |
| Approved private PostgreSQL | Missing | Encrypted service, network isolation, tested least privilege |
| Approved private object storage | Missing | Bucket policy, retention/deletion and access log review |
| Approved OCR/model runtime and data terms | Missing | Immutable image/model hashes and processing terms |
| TLS/reverse proxy | Missing | HTTPS endpoint, certificate and forwarding review |
| Backup and isolated restore | Missing | Backup identifier, restore duration and integrity checks |
| Physical iPad/desktop and weak-network test | Missing | Device/version, network condition and support result |
| Representative user/sample scope | Missing | Approved, deidentified or real-data scope as applicable |

## Required trial record

Populate this only from an approved environment. Do not place patient
identifiers, raw clinical files, credentials or unredacted logs in the public
repository. Store the source evidence privately and commit only the approved
deidentified summary.

```json
{
  "schema_version": 1,
  "status": "complete",
  "authorization": {
    "approved_use": null,
    "owner": null,
    "recorded_at": null
  },
  "environment": {
    "oidc_login_tested": null,
    "tls_verified": null,
    "private_storage_verified": null,
    "center_isolation_verified": null
  },
  "restore": {
    "status": null,
    "duration_seconds": null,
    "objects_checked": null
  },
  "trial": {
    "scope": null,
    "participants": null,
    "sessions": null,
    "critical_errors": null,
    "manual_correction_count": null,
    "total_seconds": null,
    "device_scope": []
  },
  "feedback": []
}
```

`tools/check_deployment.py --trial-evidence ...` validates the shape and
required positive evidence but cannot independently authenticate a signature or
the organization's authorization. Those remain release-owner responsibilities.

## Release boundary

Until all prerequisites have private evidence:

- keep model/analysis providers disabled unless separately approved;
- keep real clinical material outside the public repository and CI;
- do not send, sign, archive or write back to EDC;
- do not claim clinical safety or workflow-time savings;
- permit only synthetic demonstration and unaffected manual review.

If a trial has not started, that is a valid and expected current outcome.
