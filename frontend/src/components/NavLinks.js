'use client';

import { usePathname } from 'next/navigation';

const LINKS = [
  { href: '/', label: 'Pipeline' },
  { href: '/results', label: 'Results' },
  { href: '/verify', label: 'Verify' },
  { href: '/privacy', label: 'Privacy' },
];

export default function NavLinks() {
  const pathname = usePathname();
  return (
    <nav className="nav" aria-label="Primary">
      {LINKS.map((l) => {
        const active = l.href === '/' ? pathname === '/' : pathname.startsWith(l.href);
        return (
          <a key={l.href} href={l.href} aria-current={active ? 'page' : undefined} className={active ? 'active' : ''}>
            {l.label}
          </a>
        );
      })}
    </nav>
  );
}
