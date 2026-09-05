"""
VeraScan Sepolia client (CLI backend showcase).

Thin wrapper around the existing VeraScan.sol contract. No face-recognition,
search, or hashing logic lives here; it reuses ALCHEMY_RPC_URL,
DEPLOYER_PRIVATE_KEY, and CONTRACT_ADDRESS from the environment.
"""
import os

from dotenv import load_dotenv
from web3 import Web3

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))
load_dotenv(os.path.join(os.path.dirname(_HERE), ".env"))

# Minimal ABI: only the functions the CLI needs. Matches
# contracts/contracts/VeraScan.sol and frontend/src/lib/constants.js.
CONTRACT_ABI = [
    {
        "inputs": [
            {"name": "_id", "type": "bytes32"},
            {"name": "_dataHash", "type": "string"},
            {"name": "_sourceUrl", "type": "string"},
        ],
        "name": "storeRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        # NOTE: the deployed contract returns the Record struct as a single
        # tuple (verified against live return data), not five top-level
        # values. Declaring it flat makes eth_abi choke on the leading offset.
        "inputs": [{"name": "_id", "type": "bytes32"}],
        "name": "getRecord",
        "outputs": [
            {
                "name": "",
                "type": "tuple",
                "components": [
                    {"name": "dataHash", "type": "string"},
                    {"name": "sourceUrl", "type": "string"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "verifier", "type": "address"},
                    {"name": "exists", "type": "bool"},
                ],
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} environment variable is not set. "
            "Fill backend/.env (or the repo-root .env) before using the chain commands."
        )
    return value


def make_record_id(fingerprint: str) -> str:
    """Unique record id, mirroring frontend lib/blockchain.js makeRecordId.

    Returns a 0x-prefixed bytes32 hex string: keccak256("<fingerprint>-<ms>").
    """
    import time

    digest = Web3.keccak(text=f"{fingerprint}-{int(time.time() * 1000)}").hex()
    return digest if digest.startswith("0x") else "0x" + digest


def _contract():
    rpc = _require_env("ALCHEMY_RPC_URL")
    address = _require_env("CONTRACT_ADDRESS")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    return w3, w3.eth.contract(
        address=Web3.to_checksum_address(address), abi=CONTRACT_ABI
    )


def store_record(record_id: str, fingerprint: str, source_url: str) -> dict:
    """Submit storeRecord(id, fingerprint, sourceUrl); wait 1 confirmation.

    Returns {txHash, blockNumber}. Raises RuntimeError with a short message
    on any failure (unconfigured env, RPC error, reverted tx).
    """
    if not record_id or not fingerprint or not source_url:
        raise RuntimeError("record_id, fingerprint and source_url are all required.")
    rpc_key = _require_env("DEPLOYER_PRIVATE_KEY")
    w3, contract = _contract()
    try:
        account = w3.eth.account.from_key(rpc_key)
    except Exception as e:
        raise RuntimeError(f"DEPLOYER_PRIVATE_KEY is invalid: {e}")
    try:
        tx = contract.functions.storeRecord(
            Web3.to_bytes(hexstr=record_id), fingerprint, source_url
        ).build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
            }
        )
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    except Exception as e:
        raise RuntimeError(f"Blockchain store failed: {e}")
    if receipt.get("status") != 1:
        raise RuntimeError("Blockchain store failed: transaction reverted on-chain.")
    return {
        "txHash": Web3.to_hex(receipt["transactionHash"]),
        "blockNumber": int(receipt["blockNumber"]),
    }


def get_record(record_id: str) -> dict:
    """Read-only getRecord(id). Raises RuntimeError if missing/unreachable."""
    w3, contract = _contract()
    try:
        rec = contract.functions.getRecord(Web3.to_bytes(hexstr=record_id)).call()
    except Exception as e:
        raise RuntimeError(f"Blockchain read failed: {e}")
    # web3 returns the tuple as a sequence (and, for named components,
    # possibly attribute access). Unpack positionally to stay robust.
    data_hash, source_url, timestamp, verifier, exists = (
        rec[0],
        rec[1],
        rec[2],
        rec[3],
        rec[4],
    )
    if not exists:
        raise RuntimeError(f"Record {record_id} not found on-chain.")
    return {
        "recordId": record_id,
        "dataHash": data_hash,
        "sourceUrl": source_url,
        "timestamp": int(timestamp),
        "verifier": verifier,
    }
