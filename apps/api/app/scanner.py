"""C2PA Content Credentials verification and privacy-conscious summaries."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _clean_text(value: object, limit: int = 160) -> str | None:
    if not isinstance(value, str):
        return None
    text = "".join(ch for ch in value if ch.isprintable()).strip()
    return text[:limit] or None


def scan_content_credentials(path: Path) -> dict[str, object]:
    """Read C2PA data with the official CAI Python SDK when it is installed.

    Only validation state, assertion labels, and safe source-type strings are
    returned. The raw manifest is never included in a user report or log.
    """
    try:
        import c2pa
    except ImportError:
        return {
            "status": "unavailable",
            "validation_state": None,
            "assertion_labels": [],
            "digital_source_types": [],
            "details": ["The official C2PA verifier is not installed in this runtime."],
        }

    try:
        manifest = json.loads(c2pa.Reader(str(path)).json())
    except Exception as exc:
        error_kind = type(exc).__name__
        message = str(exc)
        if "ManifestNotFound" in error_kind or message.startswith("ManifestNotFound"):
            return {
                "status": "not_present",
                "validation_state": None,
                "assertion_labels": [],
                "digital_source_types": [],
                "details": ["No embedded C2PA Content Credentials manifest was found."],
            }
        logger.info("C2PA verification could not read the asset: %s", error_kind)
        return {
            "status": "error",
            "validation_state": None,
            "assertion_labels": [],
            "digital_source_types": [],
            "details": ["C2PA data could not be read or validated for this file."],
        }

    state = _clean_text(manifest.get("validation_state")) if isinstance(manifest, dict) else None
    state_folded = (state or "").casefold()
    if state_folded == "trusted":
        status = "trusted"
    elif state_folded == "valid":
        status = "valid_untrusted"
    elif state_folded == "invalid":
        status = "invalid"
    else:
        status = "unverified"

    labels: set[str] = set()
    source_types: set[str] = set()
    # The manifest's generator and issuer are descriptive strings. They do not
    # prove that a credential came from camera hardware, so do not infer that
    # property from brand-name substring matches.

    if isinstance(manifest, dict):
        active = manifest.get("active_manifest")
        manifests = manifest.get("manifests")
        active_data = manifests.get(active, {}) if isinstance(manifests, dict) and isinstance(active, str) else {}
        assertions = active_data.get("assertions", []) if isinstance(active_data, dict) else []
        if isinstance(assertions, list):
            for assertion in assertions:
                if not isinstance(assertion, dict):
                    continue
                label = _clean_text(assertion.get("label"), 120)
                if label:
                    labels.add(label)
                data = assertion.get("data")
                if isinstance(data, dict):
                    actions = data.get("actions", [])
                    if isinstance(actions, list):
                        for action in actions:
                            if isinstance(action, dict):
                                source_type = _clean_text(action.get("digitalSourceType"), 160)
                                if source_type:
                                    source_types.add(source_type)

    details = {
        "trusted": "The manifest validated and its signer chains to the configured C2PA trust list.",
        "valid_untrusted": "The manifest passed integrity validation, but its signer is not established as trusted.",
        "invalid": "The manifest failed C2PA validation; inspect the validation evidence before drawing conclusions.",
        "unverified": "A manifest was present, but the SDK did not return a recognized validation state.",
    }

    return {
        "status": status,
        "validation_state": state,
        "is_hardware_authenticated": False,
        "hardware_signer": None,
        "assertion_labels": sorted(labels)[:40],
        "digital_source_types": sorted(source_types)[:20],
        "details": [details[status]],
    }
