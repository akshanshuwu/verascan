'use client';

import { useEffect, useState } from 'react';
import BlockchainProof from '../../components/BlockchainProof';
import { verifyRecord } from '../../lib/blockchain';

export default function VerifyPage() {
  const [proof, setProof] = useState(null);
  const [verifyState, setVerifyState] = useState('');
  const [manualId, setManualId] = useState('');
  const [manualHash, setManualHash] = useState('');
  const [error, setError] = useState('');

  function clearProof() {
    try {
      sessionStorage.removeItem('verascan_proof');
    } catch {}
    setProof(null);
    setVerifyState('');
    setError('');
  }

  useEffect(() => {
    try {
      const p = sessionStorage.getItem('verascan_proof');
      if (p) setProof(JSON.parse(p));
    } catch {}
  }, []);

  async function reverify() {
    if (!proof) return;
    setVerifyState('checking');
    try {
      const v = await verifyRecord(proof.recordId, proof.dataHash);
      setVerifyState(v.matched ? 'match' : 'mismatch');
    } catch (e) {
      setError(e.message);
      setVerifyState('');
    }
  }

  async function verifyManual(e) {
    e.preventDefault();
    setError('');
    setVerifyState('checking');
    try {
      const v = await verifyRecord(manualId.trim(), manualHash.trim());
      setVerifyState(v.matched ? 'match' : 'mismatch');
      setProof({ recordId: manualId.trim(), dataHash: manualHash.trim(), txHash: '', blockNumber: v.timestamp || '', sourceUrl: v.sourceUrl });
    } catch (err) {
      setError(err.message);
      setVerifyState('');
    }
  }

  return (
    <div>
      <section className="hero">
        <div className="kicker">Step 4: Verify</div>
        <div className="hero-row">
          <div>
            <h1>Blockchain proof</h1>
            <p className="lead">Re-check any record against Ethereum Sepolia. Matching hashes mean the data is unchanged since storage.</p>
          </div>
          <ul className="spec-list" aria-label="Verification reference">
            <li><span className="k">Method</span><span className="v">read-only getRecord</span></li>
            <li><span className="k">Compare</span><span className="v">local hash == on-chain</span></li>
          </ul>
        </div>
      </section>
      {error && <div className="alert error">{error}</div>}
      {!proof && <div className="card"><p className="muted">No proof in this session yet. <a href="/">Run the pipeline</a> or verify manually below.</p></div>}
      {proof && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', margin: '4px 0 0' }}>
          <button className="btn btn-ghost" onClick={clearProof}>
            Clear session proof
          </button>
        </div>
      )}
      <BlockchainProof proof={proof} verifyState={verifyState} onReverify={reverify} />
      <div className="card">
        <div className="card-head">
          <div>
            <div className="micro-label">Manual check</div>
            <h2>Verify by ID</h2>
          </div>
        </div>
        <p className="muted">Paste a record ID and its SHA-256 hash to compare with the on-chain value.</p>
        <form onSubmit={verifyManual} className="verify-form">
          <label className="micro-label" htmlFor="vid">Record ID</label>
          <input id="vid" className="mono field" placeholder="0x…" value={manualId} onChange={(e) => setManualId(e.target.value)} />
          <label className="micro-label" htmlFor="vhash">SHA-256 hash</label>
          <input id="vhash" className="mono field" placeholder="64 hex chars" value={manualHash} onChange={(e) => setManualHash(e.target.value)} />
          <button className="btn btn-primary" type="submit">Verify</button>
        </form>
        {verifyState === 'match' && <div style={{ marginTop: 12 }}><span className="badge ok">Match: hashes equal</span></div>}
        {verifyState === 'mismatch' && <div style={{ marginTop: 12 }}><span className="badge bad">Mismatch: hashes differ</span></div>}
      </div>
    </div>
  );
}
