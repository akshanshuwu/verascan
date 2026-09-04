import { Inter, Archivo, Source_Serif_4, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import Footer from '../components/Footer';
import NavLinks from '../components/NavLinks';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' });
const grotesk = Archivo({ subsets: ['latin'], variable: '--font-grotesk', display: 'swap', weight: ['500', '600', '700', '800'] });
const serif = Source_Serif_4({ subsets: ['latin'], variable: '--font-news', display: 'swap', weight: ['400', '600'], style: ['normal', 'italic'] });
const mono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono', display: 'swap', weight: ['400', '500', '600'] });

export const metadata = {
  title: 'VeraScan — face to blockchain proof',
  description: 'Upload a face, find matching public web content, and store a tamper-proof SHA-256 fingerprint on Ethereum Sepolia.',
  openGraph: {
    title: 'VeraScan — face to blockchain proof',
    description: 'Live reverse image search with on-chain verification on Sepolia.',
    type: 'website',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${inter.variable} ${grotesk.variable} ${serif.variable} ${mono.variable}`}>
      <body>
        <header className="topbar">
          <div className="topbar-inner">
            <a className="brand" href="/" aria-label="VeraScan home">
              <span className="brand-mark" aria-hidden="true">V</span>
              <span className="brand-word">Vera<i>Scan</i></span>
            </a>
            <NavLinks />
          </div>
        </header>
        <main className="wrap">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
