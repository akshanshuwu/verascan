export default function PrivacyPage() {
  const sections = [
    {
      n: '01',
      h: 'What we process',
      body: (
        <ul className="legal-list">
          <li><strong>Face photos</strong> are processed in memory by VeraScan and are not persisted by VeraScan. A temporary cropped image may be published to an external image host solely to enable Google Lens visual search.</li>
          <li><strong>Cropped faces</strong> are temporarily uploaded to a public image host so the reverse search API can fetch them. Those hosts may retain the file under their own policy.</li>
          <li><strong>Search history</strong> (titles, URLs, hashes, transaction refs) lives only in your browser's local storage. No face images, ever.</li>
        </ul>
      ),
    },
    {
      n: '02',
      h: 'What goes on-chain',
      body: (
        <p>Only a SHA-256 fingerprint over the verified candidate image (canonical source page URL + raw image bytes), the source URL, and a timestamp are stored on Ethereum Sepolia. No face image, no embedding, no name, and no personal identifier is written to the blockchain. On-chain records are public and permanent. A match establishes biometric similarity only — never account ownership or legal identity.</p>
      ),
    },
    {
      n: '03',
      h: 'What we do not do',
      body: (
        <ul className="legal-list">
          <li>No accounts, no tracking cookies, no analytics, no face database.</li>
          <li>No sale of data. No continuous monitoring.</li>
        </ul>
      ),
    },
    {
      n: '04',
      h: 'Contact',
      body: (
        <p>For removal questions about third-party image hosts or search results, contact the respective provider directly. For VeraScan demo questions, use the GitHub repo issues page.</p>
      ),
    },
  ];
  return (
    <div className="legal">
      <section className="hero">
        <div className="kicker">Legal</div>
        <h1>Privacy Policy</h1>
        <p className="legal-date">Last updated September 6, 2026 · Hackathon demo for HH Goa 2026</p>
      </section>
      <div className="card legal-card">
        {sections.map((s) => (
          <section className="legal-section" key={s.n}>
            <div className="micro-label">{s.n}</div>
            <h2>{s.h}</h2>
            {s.body}
          </section>
        ))}
      </div>
    </div>
  );
}
