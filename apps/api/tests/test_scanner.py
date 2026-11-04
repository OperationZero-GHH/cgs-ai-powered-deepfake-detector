import json
import sys
from types import SimpleNamespace

from PIL import Image

from app.scanner import scan_content_credentials


def test_c2pa_scanner_reports_no_manifest_without_raw_metadata(tmp_path):
    image_path = tmp_path / "plain.png"
    Image.new("RGB", (24, 16), color=(80, 140, 190)).save(image_path, "PNG")

    result = scan_content_credentials(image_path)

    assert result["status"] == "not_present"
    assert result["assertion_labels"] == []
    assert "manifest" in result["details"][0].lower()


def test_invalid_manifest_cannot_claim_trusted_hardware(tmp_path, monkeypatch):
    manifest = {
        "validation_state": "invalid",
        "active_manifest": "claim",
        "manifests": {
            "claim": {
                "claim_generator": "Sony Imaging Edge",
                "signature_info": {"issuer": "Sony Camera Root"},
                "assertions": [],
            }
        },
    }

    class FakeReader:
        def __init__(self, _path):
            pass

        def json(self):
            return json.dumps(manifest)

    monkeypatch.setitem(sys.modules, "c2pa", SimpleNamespace(Reader=FakeReader))
    result = scan_content_credentials(tmp_path / "untrusted.png")

    assert result["status"] == "invalid"
    assert result["is_hardware_authenticated"] is False
    assert result["hardware_signer"] is None
    assert "trusted camera hardware signature detected" not in result["details"][0].lower()


def test_trusted_manifest_is_reported_without_hardware_or_text_corruption(tmp_path, monkeypatch):
    manifest = {
        "validation_state": "trusted",
        "active_manifest": "claim",
        "manifests": {
            "claim": {
                "claim_generator": "Sony Imaging Edge",
                "signature_info": {"issuer": "Sony Camera Root"},
                "assertions": [
                    {
                        "label": "c2pa.actions",
                        "data": {
                            "actions": [
                                {
                                    "digitalSourceType": "http://cv.iptc.org/digitalsourcetype/digitalCapture"
                                }
                            ]
                        },
                    }
                ],
            }
        },
    }

    class FakeReader:
        def __init__(self, _path):
            pass

        def json(self):
            return json.dumps(manifest)

    monkeypatch.setitem(sys.modules, "c2pa", SimpleNamespace(Reader=FakeReader))
    result = scan_content_credentials(tmp_path / "trusted.png")

    assert result["status"] == "trusted"
    assert result["validation_state"] == "trusted"
    assert result["assertion_labels"] == ["c2pa.actions"]
    assert result["digital_source_types"] == ["http://cv.iptc.org/digitalsourcetype/digitalCapture"]
    assert result["is_hardware_authenticated"] is False
    assert result["hardware_signer"] is None


def test_scanner_tolerates_malformed_active_manifest_reference(tmp_path, monkeypatch):
    class FakeReader:
        def __init__(self, _path):
            pass

        def json(self):
            return json.dumps(
                {"validation_state": "trusted", "active_manifest": [], "manifests": {}}
            )

    monkeypatch.setitem(sys.modules, "c2pa", SimpleNamespace(Reader=FakeReader))
    result = scan_content_credentials(tmp_path / "malformed.png")

    assert result["status"] == "trusted"
    assert result["assertion_labels"] == []
