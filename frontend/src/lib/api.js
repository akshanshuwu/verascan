import { API_BASE } from './constants';

export async function detectFace(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/api/detect-face`, { method: 'POST', body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Face detection failed (${res.status}): ${text.slice(0, 200)}`);
  }
  return res.json();
}

export async function searchFace(imageBase64) {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64: imageBase64 }),
  });
  if (!res.ok) throw new Error(`Search failed (${res.status})`);
  return res.json();
}

export async function hashData({ title, url, snippet, timestamp, matched_url, image_base64 }) {
  const res = await fetch(`${API_BASE}/api/hash`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, url, snippet: snippet || '', timestamp, matched_url, image_base64 }),
  });
  if (!res.ok) throw new Error(`Hash failed (${res.status})`);
  return res.json();
}
