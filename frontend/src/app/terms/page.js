export default function TermsPage() {
  const sections = [
    {
      n: '01',
      h: 'Demo only',
      body: (
        <p>VeraScan is a hackathon proof of concept. It runs on Ethereum Sepolia testnet with no monetary value. No warranty, no guarantee of accuracy, availability, or fitness for any purpose.</p>
      ),
    },
    {
      n: '02',
      h: 'Acceptable use',
      body: (
        <ul className="legal-list">
          <li>Upload only photos you have the right to use. Do not upload faces of others without consent.</li>
          <li>Do not use VeraScan for surveillance, stalking, hiring discrimination, or law enforcement decisions.</li>
          <li>Search results come from the open web via a third-party API and may be wrong, outdated, or misleading. Verify independently.</li>
        </ul>
      ),
    },
    {
      n: '03',
      h: 'Blockchain records',
      body: (
        <p>Records on Sepolia are public and cannot be deleted. Only submit hashes of data you are comfortable leaving permanently visible.</p>
      ),
    },
    {
      n: '04',
      h: 'Limitation of liability',
      body: (
        <p>To the maximum extent permitted by law, the VeraScan team is not liable for any damages arising from use of this demo.</p>
      ),
    },
  ];
  return (
    <div className="legal">
      <section className="hero">
        <div className="kicker">Legal</div>
        <h1>Terms and Conditions</h1>
        <p className="legal-date">Last updated September 6, 2026</p>
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
