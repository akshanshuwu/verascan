'use client';

import { useState } from 'react';

function CopyBtn({ value, label }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = value;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  }
  return (
    <button type="button" className="btn btn-ghost proof-copy" onClick={copy} aria-label={`Copy ${label}`}>
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

export default function BlockchainProof({ proof, verifyState, onReverify }) {
  if (!proof) return null;
  const checking = verifyState === 'checking';
  const stamp =
    verifyState === 'match' ? (
      <span className="badge ok">Match: on-chain hash equals local hash</span>
    ) : verifyState === 'mismatch' ? (
      <span className="badge bad">Mismatch: data changed since storage</span>
    ) : (
      <span className="badge pending">Stored: not yet re-verified this session</span>
    );

  const fields = [
    { k: 'Record ID', v: proof.recordId },
    { k: 'SHA-256 data hash', v: proof.dataHash },
    ...(proof.txHash ? [{ k: 'Transaction', v: proof.txHash, link: `https://sepolia.etherscan.io/tx/${proof.txHash}` }] : []),
  ];

  return (
    <section className="card proof" aria-label="Blockchain proof">
      <div className="card-head">
        <div>
          <div className="micro-label">04 · Proof · Sepolia</div>
          <h2>On-chain record</h2>
        </div>
        {stamp}
      </div>
      <p className="muted">
        Fingerprint stored via <code className="mono">storeRecord(id, hash, url)</code>. The face image never leaves your machine history. Only the hash is permanent.
      </p>

      <dl className="proof-list">
        {fields.map((f) => (
          <div className="proof-row" key={f.k}>
            <dt className="micro-label">{f.k}</dt>
            <dd>
              {f.link ? (
                <a className="mono proof-link" href={f.link} target="_blank" rel="noreferrer">{f.v}</a>
              ) : (
                <code className="mono proof-val">{f.v}</code>
              )}
            </dd>
            <CopyBtn value={f.v} label={f.k} />
          </div>
        ))}
        <div className="proof-meta-row">
          <div>
            <div className="micro-label">Block</div>
            <div className="mono">{proof.blockNumber || '-'}</div>
          </div>
          <div className="proof-source">
            <div className="micro-label">Source</div>
            <a className="res-url" href={proof.sourceUrl} target="_blank" rel="noreferrer">{proof.sourceUrl}</a>
          </div>
        </div>
      </dl>

      <div className="proof-actions">
        <button className="btn btn-secondary" onClick={onReverify} disabled={checking}>
          {checking ? 'Reading chain…' : 'Re-verify against chain'}
        </button>
        {proof.txHash && (
          <a
            className="btn btn-ghost"
            href={`https://sepolia.etherscan.io/tx/${proof.txHash}`}
            target="_blank"
            rel="noreferrer"
          >
            View on Etherscan ↗
          </a>
        )}
      </div>
    </section>
  );
}
