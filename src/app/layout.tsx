import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Nerolac Operations Dashboard | Kansai Nerolac Paints Bangladesh',
  description:
    'Enterprise Operations, Supply Chain, and Finance Control Center for Kansai Nerolac Paints Bangladesh.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="tabular-nums" style={{ backgroundColor: '#FFFFFF', color: '#0F172A' }}>
        {children}
      </body>
    </html>
  );
}
