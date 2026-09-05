"""
CLI tests (no live network, no chain, no SerpAPI spend).

Covers argparse wiring, receipt save/find/load, the in-memory tamper demo,
verify PASS/FAIL with a mocked chain reader, the scan no-match abort, and
the terminology guard for CLI copy.
"""
import base64
import json

import pytest

import cli
from services.hasher import fingerprint_evidence

RECORD_ID = "0x" + "ab" * 32
SOURCE_URL = "https://example.com/some-page"
EVIDENCE = b"\x89PNG-fake-evidence-bytes-for-cli-tests"


def _receipt(record_id=RECORD_ID, fp=None):
    fp = fp or fingerprint_evidence(SOURCE_URL, EVIDENCE)
    return {
        "recordId": record_id,
        "fingerprint": fp,
        "sourceUrl": SOURCE_URL,
        "sourceTitle": "t",
        "candidateImageUrl": "https://example.com/img.jpg",
        "imageBase64": base64.b64encode(EVIDENCE).decode("ascii"),
        "similarity": 0.94,
        "threshold": 0.50,
        "txHash": "0x" + "cd" * 32,
        "blockNumber": 1,
        "engine": "google_lens",
        "createdAt": "2026-09-05T00:00:00+00:00",
    }


def _onchain(fp=None):
    return {
        "recordId": RECORD_ID,
        "dataHash": fp or fingerprint_evidence(SOURCE_URL, EVIDENCE),
        "sourceUrl": SOURCE_URL,
        "timestamp": 1,
        "verifier": "0x" + "00" * 20,
    }


# --- argparse wiring ---


def test_parser_scan_requires_image():
    args = cli.build_parser().parse_args(["scan", "--image", "x.jpg"])
    assert args.command == "scan" and args.image == "x.jpg"


def test_parser_verify_tamper_flag():
    args = cli.build_parser().parse_args(["verify", "--record", RECORD_ID, "--tamper"])
    assert args.command == "verify" and args.tamper is True


def test_parser_rejects_unknown_command():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["nope"])


def test_make_record_id_is_0x_bytes32():
    from chain import make_record_id

    rid = make_record_id("abc123")
    assert rid.startswith("0x") and len(rid) == 66
    int(rid, 16)


# --- tamper primitive ---


def test_flip_first_byte_changes_sha_and_preserves_original():
    tampered = cli.flip_first_byte(EVIDENCE)
    assert len(tampered) == len(EVIDENCE)
    assert tampered != EVIDENCE
    assert EVIDENCE[1:] == tampered[1:]  # only the first byte changed
    import hashlib

    assert hashlib.sha256(tampered).hexdigest() != hashlib.sha256(EVIDENCE).hexdigest()


# --- receipts ---


def test_receipt_roundtrip_and_lookup(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "RECEIPTS_DIR", str(tmp_path))
    path = cli.save_receipt(_receipt())
    assert path.endswith(".json")
    assert cli.find_receipt_by_record(RECORD_ID) == path
    loaded = cli.load_receipt(path)
    assert loaded["fingerprint"] == _receipt()["fingerprint"]
    assert "PRIVATE" not in json.dumps(loaded)
    assert "SERPAPI" not in json.dumps(loaded)


def test_find_receipt_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "RECEIPTS_DIR", str(tmp_path))
    with pytest.raises(RuntimeError):
        cli.find_receipt_by_record(RECORD_ID)


# --- verify / tamper with mocked chain ---


def test_verify_pass(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "RECEIPTS_DIR", str(tmp_path))
    cli.save_receipt(_receipt())
    monkeypatch.setattr(cli.chain, "get_record", lambda _rid: _onchain())
    args = cli.build_parser().parse_args(["verify", "--record", RECORD_ID])
    assert cli.cmd_verify(args) == 0
    assert "PASS" in capsys.readouterr().out


def test_verify_fail_exit_1(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "RECEIPTS_DIR", str(tmp_path))
    cli.save_receipt(_receipt())
    monkeypatch.setattr(cli.chain, "get_record", lambda _rid: _onchain(fp="0x" + "ff" * 32))
    args = cli.build_parser().parse_args(["verify", "--record", RECORD_ID])
    assert cli.cmd_verify(args) == 1


def test_tamper_demo_leaves_receipt_untouched(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "RECEIPTS_DIR", str(tmp_path))
    path = cli.save_receipt(_receipt())
    before = open(path, "rb").read()
    monkeypatch.setattr(cli.chain, "get_record", lambda _rid: _onchain())
    args = cli.build_parser().parse_args(["verify", "--record", RECORD_ID, "--tamper"])
    assert cli.cmd_verify(args) == 0
    out = capsys.readouterr().out
    assert "ORIGINAL FINGERPRINT" in out
    assert "TAMPERED FINGERPRINT" in out
    assert "FINGERPRINT MISMATCH" in out
    assert "TAMPERING DETECTED" in out
    assert open(path, "rb").read() == before


def test_verify_without_receipt_errors():
    args = cli.build_parser().parse_args(
        ["verify", "--record", RECORD_ID, "--receipt", "/nonexistent/r.json"]
    )
    assert cli.cmd_verify(args) == 1


# --- scan edge paths (mocked services, no network) ---


def test_scan_missing_image_returns_1(tmp_path):
    args = cli.build_parser().parse_args(["scan", "--image", str(tmp_path / "no.jpg")])
    assert cli.cmd_scan(args) == 1


def test_scan_no_verified_match_aborts_without_chain(monkeypatch):
    monkeypatch.setattr(
        cli,
        "detect_face",
        lambda _b: {
            "image_base64": "data:image/jpeg;base64," + base64.b64encode(b"crop").decode(),
            "bounding_box": {"x": 1, "y": 2, "w": 3, "h": 4},
            "faces_detected": 1,
        },
    )
    monkeypatch.setattr(cli, "embed_face", lambda _b: [0.0] * 128)
    monkeypatch.setattr(
        cli,
        "search_face",
        lambda _b64: {"total_results": 0, "results": [], "best_match": None,
                      "evidence_fingerprint": None, "threshold": 0.50},
    )
    called = []
    monkeypatch.setattr(cli.chain, "store_record", lambda *a: called.append(a))
    args = cli.build_parser().parse_args(
        ["scan", "--image", "tests/fixtures/face_a.jpg"]
    )
    assert cli.cmd_scan(args) == 1
    assert called == []


def test_completion_block_shows_exact_onchain_record_id(capsys):
    record_id = "0x" + "ab" * 32
    cli.print_completion(record_id, "0x" + "cd" * 32, "f" * 64, "receipts/r.json")
    out = capsys.readouterr().out
    assert "VERIFICATION COMPLETE" in out
    assert f"Record ID: " in out and record_id in out
    assert "Transaction Hash: " in out and "0x" + "cd" * 32 in out
    assert "Fingerprint: " in out and "f" * 64 in out
    assert "Receipt: " in out and "receipts/r.json" in out
    # The transaction hash must never stand in for the record id.
    assert out.count(record_id) >= 3  # block + echoed next-step commands


def _table_rows():
    return [
        {
            "source_url": "https://www.instagram.com/reel/AbC123/",
            "thumbnail": "https://encrypted-tbn0.gstatic.com/images?q=tbn:xyz",
            "similarity": 0.94,
            "match": True,
            "usable": True,
        },
        {
            "source_url": "https://www.famousfix.com/topic/jane-doe",
            "thumbnail": "https://encrypted-tbn1.gstatic.com/images?q=tbn:abc",
            "similarity": 0.37,
            "match": False,
            "usable": True,
        },
        {
            "source_url": "",
            "thumbnail": "https://encrypted-tbn2.gstatic.com/images?q=tbn:def",
            "similarity": None,
            "match": False,
            "usable": False,
        },
    ]


def test_table_shows_full_source_page_urls_never_thumbnails(capsys):
    cli.print_candidate_table(_table_rows())
    out = capsys.readouterr().out
    assert "https://www.instagram.com/reel/AbC123/" in out
    assert "https://www.famousfix.com/topic/jane-doe" in out
    assert "encrypted-tbn" not in out
    assert "VERIFIED" in out and "BELOW THRESHOLD" in out and "NO FACE" in out


def test_table_links_become_osc8_hyperlinks_on_tty(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_use_style", lambda: True)
    cli.print_candidate_table(_table_rows()[:1])
    out = capsys.readouterr().out
    assert "\033]8;;https://www.instagram.com/reel/AbC123/" in out


def test_link_helper_plain_without_style(monkeypatch):
    monkeypatch.setattr(cli, "_use_style", lambda: False)
    assert cli._link("https://example.com/p") == "https://example.com/p"
    assert cli._link("") == ""


# --- terminology guard for CLI copy ---


def test_cli_copy_never_claims_identity():
    import pathlib

    text = pathlib.Path(cli.__file__).read_text(encoding="utf-8")
    lowered = text.lower()
    assert "identity probability" not in lowered
    assert "identity confirmed" not in lowered
    assert "% identity" not in lowered
    assert "biometric similarity" in lowered
