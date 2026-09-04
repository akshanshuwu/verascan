export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <div style={{ fontWeight: 600, color: 'var(--ink)' }}>VeraScan console</div>
          <div className="footer-rule">face → web → sha-256 → sepolia · demo only</div>
        </div>
        <div className="footer-links">
          <a href="/privacy">Privacy</a>
          <a href="/terms">Terms</a>
          <a href="https://sepolia.etherscan.io/address/0x0fb9824673d027Fb2f2fC629706C2e1E24C39408" target="_blank" rel="noreferrer">Contract ↗</a>
        </div>
      </div>
    </footer>
  );
}
