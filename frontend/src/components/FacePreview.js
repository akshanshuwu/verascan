'use client';

import { useState } from 'react';

export default function FacePreview({ originalUrl, face, facesDetected, onConfirm, onReset, busy }) {
  const [nat, setNat] = useState(null); // { w, h }
  const box = face.bounding_box;

  // Overlay as percentages of the displayed image (needs natural size).
  const pct =
    nat && nat.w > 0 && nat.h > 0
      ? {
          left: `${(box.x / nat.w) * 100}%`,
          top: `${(box.y / nat.h) * 100}%`,
          width: `${(box.w / nat.w) * 100}%`,
          height: `${(box.h / nat.h) * 100}%`,
        }
      : null;

  return (
    <section className="card fp" aria-label="Face detection result">
      <div className="card-head">
        <div>
          <div className="micro-label">02 — Detection</div>
          <h2>Face isolated</h2>
        </div>
        <span className="step-index">
          {facesDetected > 1 ? `${facesDetected} faces · largest kept` : '1 face'}
        </span>
      </div>
      <p className="muted">
        {facesDetected > 1
          ? `Found ${facesDetected} faces. The largest bounding box is used, cropped with 20% padding.`
          : 'One face found, cropped with 20% padding for search.'}
      </p>

      <div className="fp-grid">
        <figure className="fp-original">
          <div className="fp-frame">
            {originalUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={originalUrl}
                alt="Uploaded photo with detected face outlined"
                onLoad={(e) => setNat({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
              />
            )}
            {pct && (
              <div className="fp-box" style={pct} aria-hidden="true">
                <span className="fp-tag">face</span>
              </div>
            )}
          </div>
          <figcaption className="mono fp-cap">
            box x:{box.x} y:{box.y} w:{box.w} h:{box.h}
            {nat ? ` · img ${nat.w}×${nat.h}` : ''}
          </figcaption>
        </figure>

        <aside className="fp-crop-card" aria-label="Cropped face">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={face.image_base64} alt="Cropped face sent to search" />
          <div className="fp-conf">
            <div className="fp-conf-row">
              <span className="micro-label">Detection output</span>
              <span className="mono">face located</span>
            </div>
            <div className="conf-bar" role="img" aria-label="Face located indicator">
              <span style={{ width: '100%' }} />
            </div>
            <div className="fp-note">Haar cascade locator (no identity score) · 20% crop padding · JPEG q90</div>
          </div>
        </aside>
      </div>

      <div className="fp-actions">
        <button className="btn btn-primary" onClick={onConfirm} disabled={busy || !originalUrl}>
          {busy ? 'Searching…' : 'Confirm and search web'}
        </button>
        <button className="btn btn-secondary" onClick={onReset} disabled={busy}>
          Use different photo
        </button>
      </div>
    </section>
  );
}
