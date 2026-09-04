import { ethers } from 'ethers';
import { CONTRACT_ADDRESS, RPC_URL, CONTRACT_ABI } from './constants';

export function makeRecordId(dataHash) {
  return ethers.id(`${dataHash}-${Date.now()}`);
}

// Store goes through our server route so the private key never leaves the server.
export async function storeRecord(recordId, dataHash, sourceUrl) {
  const res = await fetch('/api/store', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: recordId, dataHash, sourceUrl }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || 'Blockchain store failed');
  return body; // { txHash, blockNumber, recordId }
}

export async function readRecord(recordId) {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const contract = new ethers.Contract(CONTRACT_ADDRESS, CONTRACT_ABI, provider);
  return contract.getRecord(recordId);
}

// Re-verify: compare local hash with on-chain hash via read-only call.
export async function verifyRecord(recordId, localHash) {
  const rec = await readRecord(recordId);
  const onChain = rec.dataHash || rec[0];
  const matched = onChain.toLowerCase() === localHash.toLowerCase();
  return {
    matched,
    onChainHash: onChain,
    sourceUrl: rec.sourceUrl ?? rec[1],
    timestamp: Number(rec.timestamp ?? rec[2]),
    verifier: rec.verifier ?? rec[3],
  };
}
