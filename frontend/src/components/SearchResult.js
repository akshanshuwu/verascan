'use client';

import { useState } from 'react';

export default function SearchResult({ result, onVerify, verifying, selected, index = 0, threshold = null }) {
  const [copied, setCopied] = useState(false);
  const isActive = selected?.url === result.url;
  const isBusy = verifying && isActive;
  const sim = result.similarity;
  const status = !result.usable
    ? (result.image_url ? 'NO FACE' : 'UNUSABLE')
    : (result.match ? 'SAME-FACE MATCH' : 'BELOW THRESHOLD');

  async function copyUrl() {
    try {
      await navigator.clipboard.writeText(result.url);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = result.url;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  }

  return (
    <article className={`res-row${isActive ? ' res-active' : ''}`} aria-label={`Match ${index + 1}: ${result.title || result.source}`}>
      <div className="res-thumb">
        {result.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={result.thumbnail} alt="" loading="lazy" />
        ) : (
          <div className="res-thumb-empty mono">no img</div>
        )}
        <span className="res-idx mono">{String(index + 1).padStart(2, '0')}</span>
      </div>

      <div className="res-body">
        <div className="res-top">
          <span className="chip">{result.source || 'web'}</span>
          <span className={`chip ${result.match ? 'chip-accent' : ''}`}>{status}</span>
          {isActive && <span className="chip chip-accent">selected</span>}
        </div>
        <h3 className="res-title">{result.title || 'Untitled match'}</h3>
        {result.snippet && <p className="res-snip">{result.snippet}</p>}
        <div className={`res-match${result.match ? ' res-match-pass' : ''}`} aria-label="Biometric similarity score">
          <span className="res-match-score">{sim != null ? sim.toFixed(2) : '—'}</span>
          <span className="res-match-meta">
            <strong>Biometric similarity</strong>
            <span>threshold {threshold != null ? Number(threshold).toFixed(2) : '—'}{result.faces_detected > 0 ? ` · ${result.faces_detected} face${result.faces_detected === 1 ? '' : 's'} in candidate` : ''}</span>
          </span>
        </div>
        <div className="res-url-row">
          <code className="mono res-url">{result.url}</code>
          <span className="res-url-actions">
            <button type="button" className="btn btn-ghost res-mini" onClick={copyUrl} aria-label="Copy source URL">
              {copied ? 'Copied' : 'Copy'}
            </button>
            <a className="btn btn-ghost res-mini" href={result.url} target="_blank" rel="noreferrer" aria-label="Open source in new tab">
              Open ↗
            </a>
          </span>
        </div>
      </div>

      <div className="res-side">
        <button className="btn btn-primary res-cta" onClick={() => onVerify(result)} disabled={verifying || !result.match} title={result.match ? 'Anchor verified match on-chain' : 'Below threshold — anchoring disabled'}>
          {isBusy ? 'Hashing…' : result.match ? 'Anchor on-chain' : 'Unverified'}
        </button>
        <span className="res-hint">sha-256 evidence → Sepolia</span>
      </div>
    </article>
  );
}
