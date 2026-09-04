// VeraScan search history. Browser-local only (localStorage).
// Metadata only: timestamps, result titles/URLs/sources, hashes, tx refs.
// Face images and crops are NEVER stored here (privacy: processed in memory only).

const KEY = 'verascan_history_v1';
const MAX_ENTRIES = 20;

function load() {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function save(entries) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
  } catch {
    // Storage full or unavailable. History is best-effort and never blocks the pipeline.
  }
}

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// A search run: what the web returned. No images.
export function appendSearch({ count, items }) {
  const entries = load();
  entries.unshift({
    id: uid(),
    kind: 'search',
    at: new Date().toISOString(),
    count: count ?? 0,
    items: (items || []).slice(0, 5).map((r) => ({
      title: r.title || 'Untitled match',
      url: r.url,
      source: r.source || 'web',
    })),
  });
  save(entries);
  return entries;
}

// A blockchain anchoring: the permanent proof ref. Hash + tx only.
export function appendProof({ recordId, dataHash, txHash, blockNumber, sourceUrl }) {
  const entries = load();
  entries.unshift({
    id: uid(),
    kind: 'proof',
    at: new Date().toISOString(),
    recordId,
    dataHash,
    txHash,
    blockNumber,
    sourceUrl,
  });
  save(entries);
  return entries;
}

export function listHistory() {
  return load();
}

export function removeEntry(id) {
  const entries = load().filter((e) => e.id !== id);
  save(entries);
  return entries;
}

export function clearHistory() {
  save([]);
  return [];
}
