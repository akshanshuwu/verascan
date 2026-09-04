'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import { ethers } from 'ethers';
import PipelineStepper from '../components/PipelineStepper';
import FaceUploader from '../components/FaceUploader';
import FacePreview from '../components/FacePreview';
import SearchResult from '../components/SearchResult';
import BlockchainProof from '../components/BlockchainProof';
import { HeroPoster } from '../components/HeroScene';
import { detectFace, searchFace, hashData } from '../lib/api';
import { storeRecord, verifyRecord, makeRecordId } from '../lib/blockchain';
import { appendSearch, appendProof } from '../lib/history';
import { CONTRACT_ADDRESS, RPC_URL } from '../lib/constants';

const HeroScene = dynamic(() => import('../components/HeroScene'), {
  ssr: false,
  loading: () => <HeroPoster />,
});

const SHORT_ADDR = CONTRACT_ADDRESS ? `${CONTRACT_ADDRESS.slice(0, 6)}…${CONTRACT_ADDRESS.slice(-4)}` : '…';

function ProofStrip() {
  const [count, setCount] = useState(null);
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const c = new ethers.Contract(CONTRACT_ADDRESS, ['function recordCount() view returns (uint256)'], provider);
        const n = await c.recordCount();
        if (live) setCount(String(n));
      } catch {
        if (live) setCount(null);
      }
    })();
    return () => { live = false; };
  }, []);
  return (
    <dl className="proof-strip" aria-label="Live on-chain proof">
      <div className="proof-strip-card">
        <dt className="micro-label">Records anchored</dt>
        <dd className="proof-strip-num">{count ?? '…'}</dd>
        <dd className="muted">live from Sepolia</dd>
      </div>
      <div className="proof-strip-card">
        <dt className="micro-label">Contract</dt>
        <dd className="mono proof-strip-num proof-strip-sm">{SHORT_ADDR}</dd>
        <dd className="muted"><a href={`https://sepolia.etherscan.io/address/${CONTRACT_ADDRESS}`} target="_blank" rel="noreferrer">Etherscan ↗</a></dd>
      </div>
      <div className="proof-strip-card">
        <dt className="micro-label">Confirmation</dt>
        <dd className="proof-strip-num">1 block</dd>
        <dd className="muted">Sepolia testnet</dd>
      </div>
    </dl>
  );
}

export default function Home() {
  const [step, setStep] = useState('upload');
  const [stepStates, setStepStates] = useState({});
  const [file, setFile] = useState(null);
  const [originalUrl, setOriginalUrl] = useState('');
  const [face, setFace] = useState(null);
  const [facesDetected, setFacesDetected] = useState(0);
  const [results, setResults] = useState([]);
  const [proof, setProof] = useState(null);
  const [verifyState, setVerifyState] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [threshold, setThreshold] = useState(null);
  const [bestMatch, setBestMatch] = useState(null);
  const [evidenceFingerprint, setEvidenceFingerprint] = useState(null);

  function mark(patch) {
    setStepStates((s) => ({ ...s, ...patch }));
  }

  async function handleFile(f) {
    setError('');
    setProof(null);
    setVerifyState('');
    setResults([]);
    setThreshold(null);
    setBestMatch(null);
    setEvidenceFingerprint(null);
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) {
      setError('Please upload a JPG, PNG, or WebP image.');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError('Image is too large. Maximum size is 10MB.');
      return;
    }
    setFile(f);
    setOriginalUrl(URL.createObjectURL(f));
    setBusy(true);
    setStep('detect');
    mark({ upload: 'complete', detect: 'processing' });
    try {
      const data = await detectFace(f);
      if (!data.success || !data.face) {
        mark({ detect: 'error' });
        setError(data.error || 'No face detected. Try a different photo.');
        return;
      }
      setFace(data.face);
      setFacesDetected(data.faces_detected);
      mark({ detect: 'complete' });
      sessionStorage.setItem('verascan_face', JSON.stringify(data.face));
    } catch (e) {
      mark({ detect: 'error' });
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSearch() {
    if (!face) return;
    setError('');
    setBusy(true);
    setStep('search');
    mark({ search: 'processing' });
    try {
      const data = await searchFace(face.image_base64);
      if (!data.success) {
        mark({ search: 'error' });
        setError(data.error || 'Search failed.');
        return;
      }
      if (!data.results?.length) {
        mark({ search: 'complete' });
        setError('');
        setResults([]);
        return;
      }
      setResults(data.results);
      mark({ search: 'complete', encode: 'complete' });
      sessionStorage.setItem('verascan_results', JSON.stringify(data.results));
      if (data.threshold != null) sessionStorage.setItem('verascan_threshold', String(data.threshold));
      appendSearch({ count: data.results.length, items: data.results });
      setThreshold(data.threshold ?? null);
      setBestMatch(data.best_match || null);
      setEvidenceFingerprint(data.evidence_fingerprint || null);
      if ((data.results || []).length > 0) {
        setTimeout(() => {
          const el = document.getElementById('biometric-match');
          if (!el) return;
          const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
          el.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
        }, 250);
      }
    } catch (e) {
      mark({ search: 'error' });
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(result) {
    setError('');
    setSelected(result);
    if (!result.match || !result.evidence_fingerprint) {
      setError('Below threshold: this candidate is not an independently verified face match and cannot be anchored on-chain.');
      return;
    }
    setBusy(true);
    setStep('verify');
    mark({ verify: 'processing' });
    try {
      const timestamp = String(Math.floor(Date.now() / 1000));
      // Fingerprint already computed server-side over the verified image bytes.
      const fp = result.evidence_fingerprint;
      const recordId = makeRecordId(fp);
      const stored = await storeRecord(recordId, fp, result.url);
      const p = { recordId, dataHash: fp, txHash: stored.txHash, blockNumber: stored.blockNumber, sourceUrl: result.url, candidateUrl: result.candidate_url || result.image_url || '', similarity: result.similarity, timestamp };
      setProof(p);
      mark({ verify: 'complete' });
      sessionStorage.setItem('verascan_proof', JSON.stringify(p));
      appendProof({ recordId, dataHash: fp, txHash: stored.txHash, blockNumber: stored.blockNumber, sourceUrl: result.url });
    } catch (e) {
      mark({ verify: 'error' });
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleReverify() {
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

  function reset() {
    setFile(null);
    setFace(null);
    setResults([]);
    setProof(null);
    setThreshold(null);
    setBestMatch(null);
    setEvidenceFingerprint(null);
    setStep('upload');
    setStepStates({});
    setError('');
    setOriginalUrl('');
  }

  return (
    <div>
      <section className="hero hero-syne">
        <div className="hero-syne-copy">
          <div className="kicker">Face to web to on-chain proof</div>
          <h1><span className="h1-dim">One face. Every public trace.</span><br />Proven on-chain.</h1>
          <p className="lead">
            Upload a photo. VeraScan finds matching public content and anchors
            a SHA-256 fingerprint on Ethereum Sepolia. Anyone can re-verify.
          </p>
          <div className="hero-ctas">
            <a className="btn btn-primary" href="#pipeline">Start verification</a>
            <a className="btn btn-secondary" href="#how">How it works</a>
          </div>
        </div>
        <div className="hero-syne-scene">
          <HeroScene />
        </div>
      </section>

      <ProofStrip />

      <div id="pipeline" />

      <PipelineStepper current={step} states={stepStates} />

      {error && <div className="alert error">{error}</div>}

      {!face && (
        <div className="card glass stage-upload">
          <div className="card-head">
            <div>
              <div className="micro-label">01 — Source</div>
              <h2>Upload a face photo</h2>
            </div>
            <span className="stage-num" aria-hidden="true">01</span>
          </div>
          <p className="muted">Processed in memory, never stored on the server. Min 100×100px, max 10MB. <span className="step-index">jpg · png · webp</span></p>
          <div style={{ marginTop: 16 }}>
            <FaceUploader onFile={handleFile} disabled={busy} />
          </div>
        </div>
      )}

      {face && (
        <FacePreview
          originalUrl={originalUrl}
          face={face}
          facesDetected={facesDetected}
          onConfirm={handleSearch}
          onReset={reset}
          busy={busy}
        />
      )}

      <AnimatePresence mode="popLayout">
      {results.length > 0 && (
        <motion.div
          key="results"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.22 }}
          className="card glass"
        >
          <div className="card-head">
            <div>
              <div className="micro-label">03 — Search · Google Lens live</div>
              <h2>Matching public content ({results.length})</h2>
            </div>
            <span className="stage-num" aria-hidden="true">03</span>
          </div>
          <p className="muted">Pick one result to anchor on-chain. Thumbnails are for identification only.</p>
          {threshold != null && (
            <div className="threshold-banner" role="note">
              <span>Match threshold</span>
              <strong>{threshold.toFixed(2)}</strong>
              <span className="muted">Only SAME-FACE MATCH rows can anchor.</span>
              {bestMatch
                ? <span className="badge ok">Best biometric similarity {bestMatch.similarity != null ? bestMatch.similarity.toFixed(4) : '—'}</span>
                : <span className="badge pending">No verified match yet</span>}
            </div>
          )}
          {results.map((r, i) => (
            <SearchResult key={r.url} index={i} result={r} onVerify={handleVerify} verifying={busy} selected={selected} threshold={threshold} />
          ))}
        </motion.div>
      )}
      </AnimatePresence>

      {face && results.length === 0 && stepStates.search === 'complete' && (
        <div className="card">
          <h2>No matching content found on the web.</h2>
          <p className="muted">Try a clearer front-facing photo, or a face with more public presence. Nothing was written to the blockchain.</p>
        </div>
      )}

      {stepStates.search === 'complete' && results.length > 0 && (
        <div className="card" id="biometric-match" aria-label="Independent verification stages">
          <div className="card-head">
            <div>
              <div className="micro-label">Independent verification</div>
              <h2>Biometric similarity match</h2>
            </div>
          </div>
          <ul className="spec-list" aria-label="Verification stages">
            <li><span className="k">Face detected</span><span className="v">✓</span></li>
            <li><span className="k">Face encoded (SFace 128-D)</span><span className="v">✓</span></li>
            <li><span className="k">Lens search</span><span className="v">✓ genuine external discovery</span></li>
            <li><span className="k">Candidates found</span><span className="v">{results.length}</span></li>
            <li><span className="k">Candidate verification</span><span className="v">✓ each face compared</span></li>
            <li><span className="k">Best biometric similarity</span><span className="v">{bestMatch && bestMatch.similarity != null ? bestMatch.similarity.toFixed(4) : '—'}</span></li>
            <li><span className="k">Match threshold</span><span className="v">{threshold != null ? threshold.toFixed(2) : '—'}</span></li>
            <li><span className="k">Match confirmed</span><span className="v">{bestMatch ? '✓ SAME-FACE MATCH' : '— below threshold, anchoring disabled'}</span></li>
            <li><span className="k">SHA-256 evidence fingerprint</span><span className="v">{evidenceFingerprint ? `${evidenceFingerprint.slice(0, 20)}…` : '—'}</span></li>
          </ul>
          <p className="muted" style={{ marginTop: 10 }}>Biometric similarity only — not identity, not account ownership. The blockchain later verifies evidence integrity.</p>
        </div>
      )}

      <BlockchainProof proof={proof} verifyState={verifyState} onReverify={handleReverify} />

      <div className="card" id="how">
        <div className="card-head">
          <div>
            <div className="micro-label">How it works</div>
            <h2>Four stages, one proof</h2>
          </div>
        </div>
        <div className="stages-grid">
          <div className="stage-card">
            <div className="stage-num" aria-hidden="true">01</div>
            <h3>Upload</h3>
            <p className="muted">JPG, PNG or WebP up to 10MB. Processed in memory, never stored on the server.</p>
          </div>
          <div className="stage-card">
            <div className="stage-num" aria-hidden="true">02</div>
            <h3>Detect</h3>
            <p className="muted">OpenCV Haar Cascades isolate the largest face and crop it with 20% padding.</p>
          </div>
          <div className="stage-card">
            <div className="stage-num" aria-hidden="true">03</div>
            <h3>Search</h3>
            <p className="muted">Live Google Lens discovery (exact + visual matches). SFace verifies each candidate face independently.</p>
          </div>
          <div className="stage-card">
            <div className="stage-num" aria-hidden="true">04</div>
            <h3>Verify</h3>
            <p className="muted">SHA-256 over the verified image bytes, stored on Sepolia. Re-verify free, forever, by anyone.</p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <div className="micro-label">Architecture</div>
            <h2>Face to chain, no detours</h2>
          </div>
        </div>
        <ol className="arch-flow" aria-label="System architecture">
          <li><span className="mono arch-node">Browser<br />Next.js</span></li>
          <li><span className="mono arch-node">FastAPI :8000<br />detect · search · hash</span></li>
          <li><span className="mono arch-node">SerpAPI<br />Google Lens</span></li>
          <li><span className="mono arch-node">Sepolia<br />VeraScan.sol</span></li>
        </ol>
        <p className="muted" style={{ marginTop: 12 }}>Images never touch the chain and never rest on the server. Only the hash and source URL go on-chain.</p>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <div className="micro-label">Reference</div>
            <h2>How verification works</h2>
          </div>
        </div>
        <ul className="spec-list" aria-label="Verification steps">
          <li><span className="k">1 · Hash</span><span className="v">sha256(matched_url + image_bytes)</span></li>
          <li><span className="k">2 · Store</span><span className="v">storeRecord(id, hash, url)</span></li>
          <li><span className="k">3 · Re-verify</span><span className="v">getRecord(id) == local hash</span></li>
          <li><span className="k">Contract</span><span className="v">{process.env.NEXT_PUBLIC_CONTRACT_ADDRESS}</span></li>
        </ul>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <div className="micro-label">Honest limits</div>
            <h2>What VeraScan cannot do</h2>
          </div>
        </div>
        <ul className="limits-list">
          <li>No public face, no results. Private accounts never appear.</li>
          <li>SerpAPI free tier allows 100 searches per month.</li>
          <li>Sepolia is a testnet. Nothing here has monetary value.</li>
          <li>Detection needs front-facing, well-lit photos.</li>
          <li>Results mirror the open web, which can be wrong or stale.</li>
        </ul>
      </div>
    </div>
  );
}
