export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CONTRACT_ADDRESS || '';
export const RPC_URL = process.env.NEXT_PUBLIC_ALCHEMY_RPC_URL || '';

export const CONTRACT_ABI = [
  'function storeRecord(bytes32,string,string)',
  'function verifyRecord(bytes32,string) returns (bool)',
  'function getRecord(bytes32) view returns (tuple(string dataHash,string sourceUrl,uint256 timestamp,address verifier,bool exists))',
];
