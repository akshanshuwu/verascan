"""
VeraScan backend/CLI showcase.

Reuses the existing pipeline -- face detection, YuNet/SFace verification,
SerpAPI Google Lens search, SHA-256 evidence fingerprinting -- and adds a
terminal demonstration layer plus local JSON receipts for re-verification.

Nothing here duplicates the service implementations; every real operation
calls into services/ or chain.py.
"""
import argparse
import base64
import datetime
import json
import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# backend/.env holds SERPAPI_KEY; the repo-root .env holds the chain keys.
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
load_dotenv(os.path.join(os.path.dirname(_BACKEND_DIR), ".env"))

from services.face_detection import detect_face
from services.face_recognition import embed_face
from services.hasher import fingerprint_evidence
from services.reverse_search import _download_image, search_face

import chain

RECEIPTS_DIR = os.path.join(_BACKEND_DIR, "receipts")

DIV = "=" * 60

# NOTE (terminology): scores are always "biometric similarity" / "cosine
# similarity". The chain verifies the integrity of the recorded evidence
# fingerprint; it does not prove identity or account ownership.

# --- Minimal terminal styling (ANSI only, no new dependencies) ---
# Colors are sparing and semantic: cyan = structure, green = success,
# yellow = caution, red = failure. Automatically disabled when output is
# piped/captured or NO_COLOR is set, so logs and tests stay plain text.
_ANSI = {
    "cyan": "36",
    "green": "32",
    "yellow": "33",
    "red": "31",
    "bold": "1",
    "dim": "2",
}


def _use_style() -> bool:
    """True only on an interactive terminal without NO_COLOR set."""
    if os.getenv("NO_COLOR") is not None:
        return False
    try:
        return bool(sys.stdout.isatty())
    except Exception:
        return False


def _paint(code: str, text: str) -> str:
    if not _use_style():
        return text
    return f"\033[{code}m{text}\033[0m"


def _c(name: str, text: str) -> str:
    return _paint(_ANSI[name], text)


def _link(url: str) -> str:
    """Full URL, clickable via OSC 8 on terminals that support it.

    The visible text is always the complete URL so it stays copyable
    everywhere; non-terminal output gets the plain URL.
    """
    if not url or not _use_style():
        return url or ""
    return f"\033]8;;{url}\033\\{url}\033]8;;\033\\"


def _ok(text: str) -> str:
    return f"      {_c('green', '+')} {text}"


def _err(text: str) -> str:
    return f"      {_c('red', 'x')} {text}"


def _stage(title: str) -> str:
    return _c("cyan", title)


def _status_chip(status: str) -> str:
    if status == "VERIFIED":
        return _c("green", status)
    if status == "BELOW THRESHOLD":
        return _c("yellow", status)
    return _c("dim", status)  # NO FACE and similar neutral states


def short_source(url: str) -> str:
    """Domain label for the candidate table, e.g. instagram.com."""
    try:
        host = urlparse(url or "").netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def flip_first_byte(data: bytes) -> bytes:
    """Return a copy with one bit flipped in the first byte (tamper demo)."""
    if not data:
        raise ValueError("Cannot tamper with empty evidence bytes.")
    mutated = bytearray(data)
    mutated[0] ^= 0x01
    return bytes(mutated)


def receipt_path_for(record_id: str, when: datetime.datetime) -> str:
    stamp = when.strftime("%Y%m%dT%H%M%S")
    return os.path.join(RECEIPTS_DIR, f"receipt_{stamp}_{record_id[2:10]}.json")


def save_receipt(receipt: dict) -> str:
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    path = receipt_path_for(
        receipt["recordId"],
        datetime.datetime.fromisoformat(receipt["createdAt"]),
    )
    with open(path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    return path


def find_receipt_by_record(record_id: str) -> str:
    """Locate the local receipt for a record id. Raises RuntimeError if absent."""
    if not os.path.isdir(RECEIPTS_DIR):
        raise RuntimeError(
            "No local receipts found. Run a scan first: "
            "python main.py scan --image <photo>"
        )
    wanted = (record_id or "").lower()
    for fn in sorted(os.listdir(RECEIPTS_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(RECEIPTS_DIR, fn)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        if str(data.get("recordId", "")).lower() == wanted:
            return path
    raise RuntimeError(
        f"No local receipt for record {record_id}. "
        "Run the scan on this machine first: python main.py scan --image <photo>"
    )


def load_receipt(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Second-line indent: aligns the full page URL under the Source column.
_URL_INDENT = " " * 23


def print_candidate_table(results: list) -> None:
    print(_c("dim", "      Candidate        Source              Similarity       Status"))
    print(_c("dim", "      ------------------------------------------------------------"))
    for i, r in enumerate(results, 1):
        sim = r.get("similarity")
        sim_text = f"{sim:.2f}" if isinstance(sim, (int, float)) else "-"
        if r.get("match"):
            status = "VERIFIED"
        elif not r.get("usable"):
            status = "NO FACE"
        else:
            status = "BELOW THRESHOLD"
        print(
            f"      #{i:<16} {(short_source(r.get('source_url') or '')[:18]):<19} "
            f"{sim_text:<16} {_status_chip(status)}"
        )
        # Full source PAGE url (where the evidence was found), never the
        # image CDN/thumbnail URL. Own line: always complete and copyable.
        page_url = r.get("source_url") or ""
        if page_url:
            print(f"{_URL_INDENT}{_c('dim', _link(page_url))}")


def print_completion(record_id: str, tx_hash: str, fingerprint: str, receipt_path: str) -> None:
    """Final VERIFICATION COMPLETE block.

    record_id must be the exact on-chain recordId (same value written into
    the receipt), never the transaction hash.
    """
    print(_c("green", DIV))
    print(_c("green", "VERIFICATION COMPLETE"))
    print(_c("green", DIV))
    print()
    print(f"Record ID:        {_c('bold', record_id)}")
    print(f"Transaction Hash: {_c('bold', tx_hash)}")
    print(f"Fingerprint:      {fingerprint}")
    print(f"Receipt:          {_c('cyan', receipt_path)}")
    print()
    print("Next steps:")
    print(f"  python main.py verify --record {record_id}")
    print(f"  python main.py verify --record {record_id} --tamper")
    print()
    print("Note: the chain verifies the integrity of the recorded evidence")
    print("fingerprint. It does not prove identity or account ownership.")


def cmd_scan(args: argparse.Namespace) -> int:
    image_path = args.image
    if not os.path.isfile(image_path):
        print(f"Error: image not found: {image_path}", file=sys.stderr)
        return 1
    with open(image_path, "rb") as f:
        raw_bytes = f.read()
    if not raw_bytes:
        print("Error: image file is empty.", file=sys.stderr)
        return 1

    print(_c("cyan", DIV))
    print(_c("cyan", "VERASCAN -- BACKEND PIPELINE"))
    print(_c("cyan", DIV))
    print()
    print(_stage("[1/7] FACE DETECTION"))
    try:
        detection = detect_face(raw_bytes)
    except ValueError as e:
        print(_err(str(e)), file=sys.stderr)
        return 1
    box = detection["bounding_box"]
    print(_ok("Face detected"))
    print(
        _ok(
            "Primary face selected "
            f"(box x:{box['x']} y:{box['y']} w:{box['w']} h:{box['h']}, "
            f"{detection['faces_detected']} face(s) found)"
        )
    )
    print()
    print(_stage("[2/7] FACE ENCODING"))
    crop_b64 = detection["image_base64"]
    crop_bytes = base64.b64decode(crop_b64.split(",", 1)[1])
    try:
        embedding = embed_face(crop_bytes)
    except ValueError as e:
        print(_err(f"Face encoding failed: {e}"), file=sys.stderr)
        return 1
    print(_ok("YuNet + SFace"))
    print(_ok(f"{len(embedding)}-dimensional embedding generated"))
    print()
    print(_stage("[3/7] REVERSE IMAGE SEARCH"))
    try:
        result = search_face(crop_b64)
    except RuntimeError as e:
        print(_err(f"Search failed: {e}"), file=sys.stderr)
        return 1
    print(_ok("Google Lens search completed"))
    print(_ok(f"{result['total_results']} candidate(s) discovered"))
    print()
    print(_stage("[4/7] CANDIDATE VERIFICATION"))
    print()
    if result["results"]:
        print_candidate_table(result["results"])
    else:
        print(_c("yellow", "      No candidates discovered for this face."))
    print()
    print(_stage("[5/7] BEST VERIFIED MATCH"))
    best = result.get("best_match")
    if not best:
        print(_err("No candidate passed the biometric similarity threshold"), file=sys.stderr)
        print(
            f"        (threshold {result.get('threshold'):.2f}). Nothing was written on-chain.",
            file=sys.stderr,
        )
        print("        Try a clearer front-facing photo with more public presence.", file=sys.stderr)
        return 1
    print(_ok("Candidate selected"))
    print(_ok(f"Biometric similarity: {best['similarity']:.2f} (cosine similarity)"))
    print(_ok(f"Source URL: {_link(best['source_url'])}"))
    print()
    print(_stage("[6/7] EVIDENCE FINGERPRINT"))
    fingerprint = result["evidence_fingerprint"]
    # Re-fetch the exact verified bytes for the receipt and confirm they
    # reproduce the fingerprint the search pipeline already computed.
    evidence_bytes = _download_image(best["image_url"]) if best.get("image_url") else None
    if not evidence_bytes:
        print(_err("Could not re-fetch the verified evidence bytes."), file=sys.stderr)
        return 1
    if fingerprint_evidence(best["source_url"], evidence_bytes) != fingerprint:
        print(
            _err(
                "Evidence bytes changed between verification and receipt; "
                "aborting rather than anchoring."
            ),
            file=sys.stderr,
        )
        return 1
    print(_ok("SHA-256 generated"))
    print(_ok(f"Fingerprint: {fingerprint}"))
    print()
    print(_stage("[7/7] ETHEREUM SEPOLIA"))
    record_id = chain.make_record_id(fingerprint)
    try:
        stored = chain.store_record(record_id, fingerprint, best["source_url"])
    except RuntimeError as e:
        print(_err(str(e)), file=sys.stderr)
        return 1
    print(_ok("Transaction submitted"))
    print(_ok("Transaction confirmed"))
    print(_ok(f"Transaction hash: {stored['txHash']}"))
    # Read the record back and confirm the chain holds our fingerprint.
    try:
        onchain = chain.get_record(record_id)
    except RuntimeError as e:
        print(_err(f"Read-back failed: {e}"), file=sys.stderr)
        return 1
    if onchain["dataHash"].lower() != fingerprint.lower():
        print(_err("Read-back mismatch: on-chain fingerprint differs."), file=sys.stderr)
        return 1
    print(_ok("Read-back verified: on-chain fingerprint matches"))
    print()
    receipt = {
        "recordId": record_id,
        "fingerprint": fingerprint,
        "sourceUrl": best["source_url"],
        "sourceTitle": best.get("title", ""),
        "candidateImageUrl": best.get("image_url", ""),
        "imageBase64": base64.b64encode(evidence_bytes).decode("ascii"),
        "similarity": best["similarity"],
        "threshold": result.get("threshold"),
        "txHash": stored["txHash"],
        "blockNumber": stored["blockNumber"],
        "engine": "google_lens",
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    path = save_receipt(receipt)
    # Final block prints the exact on-chain recordId (same value stored in
    # the receipt), so verify/--tamper can be copy-pasted directly.
    print_completion(record_id, stored["txHash"], fingerprint, path)
    return 0


def _load_verify_context(args: argparse.Namespace):
    receipt_path = args.receipt or find_receipt_by_record(args.record)
    receipt = load_receipt(receipt_path)
    if receipt.get("recordId", "").lower() != (args.record or "").lower():
        raise RuntimeError(
            f"Receipt {receipt_path} belongs to a different record. "
            "Pass --receipt explicitly if you keep multiple receipts."
        )
    onchain = chain.get_record(args.record)
    evidence_bytes = base64.b64decode(receipt["imageBase64"])
    expected = fingerprint_evidence(receipt["sourceUrl"], evidence_bytes)
    return receipt, receipt_path, onchain, evidence_bytes, expected


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        receipt, receipt_path, onchain, _evidence, expected = _load_verify_context(args)
    except (RuntimeError, OSError, ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.tamper:
        tampered_bytes = flip_first_byte(base64.b64decode(receipt["imageBase64"]))
        tampered = fingerprint_evidence(receipt["sourceUrl"], tampered_bytes)
        print(_stage("VERASCAN -- TAMPER DEMO"))
        print(f"ORIGINAL FINGERPRINT: {onchain['dataHash']}")
        print(f"TAMPERED FINGERPRINT: {_c('yellow', tampered)}")
        print(_c("red", "x FINGERPRINT MISMATCH"))
        print(_c("green", "+ TAMPERING DETECTED"))
        print("(local receipt left unchanged)")
        return 0

    match = onchain["dataHash"].lower() == expected.lower()
    print(_stage("VERASCAN -- RECORD VERIFICATION"))
    print(f"Record:        {_c('bold', onchain['recordId'])}")
    print(f"Source URL:    {onchain['sourceUrl']}")
    print(f"Verifier:      {onchain['verifier']}")
    print(f"Tx hash:       {receipt.get('txHash', '-')}")
    print(f"Block:         {receipt.get('blockNumber', '-')}")
    print(f"Local print:   {expected}")
    print(f"On-chain:      {onchain['dataHash']}")
    if match:
        print(_c("green", "PASS: on-chain evidence fingerprint matches the local evidence."))
    else:
        print(
            _c("red", "FAIL: on-chain evidence fingerprint does NOT match."),
            file=sys.stderr,
        )
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "VeraScan backend pipeline: detect a face, discover matching public "
            "web content via Google Lens, verify with YuNet+SFace biometric "
            "similarity, fingerprint the evidence with SHA-256, and anchor it "
            "on Ethereum Sepolia. The chain verifies evidence integrity only."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser(
        "scan",
        help="Run the end-to-end pipeline on an image and anchor the match on-chain.",
    )
    scan.add_argument("--image", required=True, help="Path to a JPG/PNG/WebP photo.")
    scan.set_defaults(func=cmd_scan)

    verify = sub.add_parser(
        "verify",
        help="Re-verify a blockchain record against its local receipt.",
    )
    verify.add_argument("--record", required=True, help="On-chain record id (0x bytes32).")
    verify.add_argument(
        "--tamper",
        action="store_true",
        help="One-byte in-memory tamper demo; receipt file is never modified.",
    )
    verify.add_argument(
        "--receipt",
        default=None,
        help="Explicit receipt path (default: look up by record id).",
    )
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)
