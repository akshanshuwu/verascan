'use client';

import { useEffect, useState } from 'react';
import SearchResult from '../../components/SearchResult';
import { hashData } from '../../lib/api';
import { storeRecord, makeRecordId } from '../../lib/blockchain';
import { appendProof, listHistory, removeEntry, clearHistory } from '../../lib/history';

function fmtTime(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function ResultsPage() {
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [proof, setProof] = useState(null);
  const [error, setError] = useState('');
  const [archive, setArchive] = useState([]);
  const [confirmClear, setConfirmClear] = useState(false);
  const [threshold, setThreshold] = useState(() => {
    try {
      const t = sessionStorage.getItem('verascan_threshold');
      return t ? parseFloat(t) : null;
    } catch {
      return null;
    }
  });

  function clearCurrent() {
    try {
      sessionStorage.removeItem('verascan_results');
      sessionStorage.removeItem('verascan_proof');
      sessionStorage.removeItem('verascan_threshold');
    } catch {}
    setResults([]);
    setSelected(null);
    setProof(null);
    setThreshold(null);
    setError('');
  }

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem('verascan_results');
      if (raw) setResults(JSON.parse(raw));
      const p = sessionStorage.getItem('verascan_proof');
      if (p) setProof(JSON.parse(p));
    } catch {}
    setArchive(listHistory());
  }, []);

  async function handleVerify(result) {
    setError('');
    setSelected(result);
    if (!result.match || !result.evidence_fingerprint) {
      setError('Below threshold: this candidate is not an independently verified face match and cannot be anchored on-chain.');
      return;
    }
    setBusy(true);
    try {
      const timestamp = String(Math.floor(Date.now() / 1000));
      const fp = result.evidence_fingerprint;
      const recordId = makeRecordId(fp);
      const stored = await storeRecord(recordId, fp, result.url);
      const p = { recordId, dataHash: fp, txHash: stored.txHash, blockNumber: stored.blockNumber, sourceUrl: result.url, candidateUrl: result.candidate_url || result.image_url || '', similarity: result.similarity, timestamp };
      setProof(p);
      sessionStorage.setItem('verascan_proof', JSON.stringify(p));
      appendProof({ recordId, dataHash: fp, txHash: stored.txHash, blockNumber: stored.blockNumber, sourceUrl: result.url });
      setArchive(listHistory());
      window.location.href = '/verify';
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <section className="hero">
        <div className="kicker">Step 3: Search</div>
        <h1>Web matches</h1>
        <p className="lead">Live Google Lens results for your cropped face. If you landed here directly, start from the pipeline home page.</p>
      </section>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        <div className="card-head">
          <div>
            <div className="micro-label">Session results</div>
            <h2>Web matches{results.length > 0 ? ` (${results.length})` : ''}</h2>
          </div>
          {results.length > 0 && (
            <button className="btn btn-ghost" onClick={clearCurrent} disabled={busy}>
              Clear results
            </button>
          )}
        </div>
        {results.length === 0 && <p className="muted">No results in this session yet. <a href="/">Go to upload</a>.</p>}
        {threshold != null && results.length > 0 && (
          <div className="threshold-banner" role="note">
            <span>Match threshold</span>
            <strong>{threshold.toFixed(2)}</strong>
            <span className="muted">Only SAME-FACE MATCH rows can anchor.</span>
          </div>
        )}
        {results.map((r, i) => (
          <SearchResult key={r.url} index={i} result={r} onVerify={handleVerify} verifying={busy} selected={selected} threshold={threshold} />
        ))}
      </div>
      {proof && (
        <div className="card">
          <h2>Stored</h2>
          <p className="muted mono">{proof.txHash} (block {proof.blockNumber})</p>
          <p><a href="/verify">View verification proof</a></p>
        </div>
      )}

      <div className="card">
        <div className="card-head">
          <div>
            <div className="micro-label">Archive · this browser</div>
            <h2>Previous searches ({archive.length})</h2>
          </div>
          {archive.length > 0 && (
            <button
              className="btn btn-ghost"
              onClick={() => {
                if (!confirmClear) {
                  setConfirmClear(true);
                  setTimeout(() => setConfirmClear(false), 3000);
                  return;
                }
                setArchive(clearHistory());
                setConfirmClear(false);
              }}
            >
              {confirmClear ? 'Click again to confirm wipe' : 'Clear all'}
            </button>
          )}
        </div>
        {archive.length === 0 && (
          <p className="muted">Nothing archived yet. Each search and each on-chain proof lands here. Metadata only, no face images.</p>
        )}
        {archive.map((e) => (
          <article className="hist-entry" key={e.id} style={{ borderTop: '1px solid var(--line)', paddingTop: 14, marginTop: 14 }}>
            <div className="card-head">
              <div>
                <div className="micro-label">
                  {e.kind === 'search' ? 'Search run' : 'On-chain proof'} · {fmtTime(e.at)}
                </div>
                <h3>{e.kind === 'search' ? `${e.count} match${e.count === 1 ? '' : 'es'} found` : 'Anchored on Sepolia'}</h3>
              </div>
              <button className="btn btn-ghost res-mini" onClick={() => setArchive(removeEntry(e.id))} aria-label="Delete this history entry">
                Delete
              </button>
            </div>
            {e.kind === 'search' && (
              <ul className="hist-items">
                {(e.items || []).map((it) => (
                  <li key={it.url}>
                    <span className="chip">{it.source}</span>
                    <span className="hist-title">{it.title}</span>
                    <a className="res-url" href={it.url} target="_blank" rel="noreferrer">{it.url}</a>
                  </li>
                ))}
              </ul>
            )}
            {e.kind === 'proof' && (
              <ul className="spec-list" aria-label="Proof reference">
                <li><span className="k">Record</span><span className="v">{e.recordId}</span></li>
                <li><span className="k">Hash</span><span className="v">{(e.dataHash || '').slice(0, 24)}…</span></li>
                <li>
                  <span className="k">Tx</span>
                  <span className="v"><a href={`https://sepolia.etherscan.io/tx/${e.txHash}`} target="_blank" rel="noreferrer">block {e.blockNumber} ↗</a></span>
                </li>
                <li><span className="k">Source</span><span className="v">{e.sourceUrl}</span></li>
              </ul>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
