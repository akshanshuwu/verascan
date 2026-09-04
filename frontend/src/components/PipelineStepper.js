'use client';

import { motion } from 'framer-motion';

const STEPS = [
  { key: 'upload', label: 'Upload', hint: 'Face photo in' },
  { key: 'detect', label: 'Detect', hint: 'Crop + preview' },
  { key: 'search', label: 'Search', hint: 'Web matches' },
  { key: 'verify', label: 'Verify', hint: 'On-chain proof' },
];

function glyph(state, i) {
  if (state === 'complete') return '✓';
  if (state === 'error') return '!';
  return String(i + 1);
}

export default function PipelineStepper({ current, states = {} }) {
  const order = STEPS.map((s) => s.key);
  const activeIdx = Math.max(0, order.indexOf(current));
  const resolved = STEPS.map((s, i) => {
    const explicit = states[s.key];
    const state =
      explicit || (i < activeIdx ? 'complete' : i === activeIdx ? 'active' : 'pending');
    const sub =
      state === 'complete'
        ? 'Done'
        : state === 'processing'
          ? 'Working…'
          : state === 'error'
            ? 'Needs attention'
            : state === 'active'
              ? s.hint
              : s.hint;
    return { ...s, state, sub };
  });
  const doneCount = resolved.filter((s) => s.state === 'complete').length;
  const progress = Math.min(100, (doneCount / (STEPS.length - 1)) * 100);

  return (
    <nav className="rail-stepper" aria-label="Pipeline progress">
      <div className="rail-track" aria-hidden="true">
        <motion.div
          className="rail-fill"
          initial={false}
          animate={{ width: `${progress}%` }}
          transition={{ type: 'spring', stiffness: 120, damping: 20 }}
        />
      </div>
      <ol>
        {resolved.map((s, i) => (
          <li key={s.key} className={`rs-node rs-${s.state}`} aria-current={i === activeIdx ? 'step' : undefined}>
            <span className="rs-dot" aria-hidden="true">
              <motion.span
                key={s.state}
                initial={{ scale: 0.85, opacity: 0.6 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.18 }}
                className="rs-glyph"
              >
                {glyph(s.state, i)}
              </motion.span>
              {s.state === 'processing' && <span className="rs-ping" aria-hidden="true" />}
            </span>
            <span className="rs-text">
              <span className="rs-label">
                <span className="rs-idx mono">0{i + 1}</span> {s.label}
              </span>
              <span className="rs-sub">{s.sub}</span>
            </span>
          </li>
        ))}
      </ol>
    </nav>
  );
}
