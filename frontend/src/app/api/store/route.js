import { ethers } from 'ethers';

export async function POST(req) {
  try {
    const { id, dataHash, sourceUrl } = await req.json();
    if (!id || !dataHash || !sourceUrl) {
      return Response.json({ error: 'id, dataHash and sourceUrl are required' }, { status: 400 });
    }
    const rpc = process.env.ALCHEMY_RPC_URL;
    const key = process.env.DEPLOYER_PRIVATE_KEY;
    const addr = process.env.CONTRACT_ADDRESS;
    if (!rpc || !key || !addr) {
      return Response.json({ error: 'Server blockchain env not configured' }, { status: 500 });
    }
    const provider = new ethers.JsonRpcProvider(rpc);
    const wallet = new ethers.Wallet(key, provider);
    const abi = ['function storeRecord(bytes32,string,string)'];
    const contract = new ethers.Contract(addr, abi, wallet);
    const tx = await contract.storeRecord(id, dataHash, sourceUrl);
    const receipt = await tx.wait(1);
    return Response.json({
      txHash: receipt.hash,
      blockNumber: receipt.blockNumber,
      recordId: id,
    });
  } catch (e) {
    const msg = e?.reason || e?.shortMessage || e?.message || 'store failed';
    return Response.json({ error: msg.slice(0, 500) }, { status: 500 });
  }
}
