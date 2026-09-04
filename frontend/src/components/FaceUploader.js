'use client';

import { useRef, useState } from 'react';

const ACCEPT = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_BYTES = 10 * 1024 * 1024;

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export default function FaceUploader({ onFile, disabled }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [localError, setLocalError] = useState('');
  const [meta, setMeta] = useState(null); // { name, size, dims, url }

  function validate(f) {
    if (!ACCEPT.includes(f.type)) return 'Please upload a JPG, PNG, or WebP image.';
    if (f.size > MAX_BYTES) return 'Image is too large. Maximum size is 10MB.';
    if (f.size === 0) return 'That file is empty. Pick another photo.';
    return '';
  }

  function inspect(f) {
    const url = URL.createObjectURL(f);
    const img = new Image();
    img.onload = () => {
      setMeta({ name: f.name, size: f.size, dims: `${img.naturalWidth}×${img.naturalHeight}`, url });
    };
    img.onerror = () => setMeta({ name: f.name, size: f.size, dims: '', url });
    img.src = url;
  }

  function accept(f) {
    setLocalError('');
    const err = validate(f);
    if (err) {
      setLocalError(err);
      setMeta(null);
      return;
    }
    inspect(f);
    onFile(f);
  }

  function onInput(e) {
    const f = e.target.files?.[0];
    if (f) accept(f);
    e.target.value = '';
  }

  function onDrop(e) {
    e.preventDefault();
    setDrag(false);
    if (disabled) return;
    const f = e.dataTransfer.files?.[0];
    if (f) accept(f);
  }

  function clear() {
    setMeta(null);
    setLocalError('');
    if (inputRef.current) inputRef.current.value = '';
  }

  return (
    <div>
      <div
        className={`dz${drag ? ' dz-drag' : ''}${disabled ? ' dz-disabled' : ''}`}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        aria-label="Upload a face photo"
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (disabled) return;
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={onInput}
          disabled={disabled}
          tabIndex={-1}
          aria-hidden="true"
        />
        <div className="micro-label">01 · Source image</div>
        <div className="dz-title">{drag ? 'Release to load photo' : 'Drop a face photo, or click to browse'}</div>
        <div className="dz-sub">JPG · PNG · WebP. Max 10MB, min 100×100px. Front-facing, well lit.</div>
        <div className="dz-formats">
          <span>JPG</span><span>PNG</span><span>WEBP</span>
        </div>
      </div>

      {localError && <div className="alert error" role="alert">{localError}</div>}

      {meta && !localError && (
        <div className="file-chip">
          {meta.url && <img src={meta.url} alt="" aria-hidden="true" />}
          <div className="file-chip-body">
            <div className="file-chip-name">{meta.name}</div>
            <div className="file-chip-meta mono">
              {formatBytes(meta.size)}{meta.dims ? ` · ${meta.dims}px` : ''}
            </div>
          </div>
          <button type="button" className="btn btn-ghost" onClick={clear} disabled={disabled} aria-label="Clear selected file">
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
