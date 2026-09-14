import type { Metadata } from 'next';
import './globals.css';
const origin = process.env.APP_URL || process.env.RENDER_EXTERNAL_URL || 'http://localhost:3000';
export const metadata: Metadata = {
  metadataBase: new URL(origin),
  title: 'LakshyaInstitute | Student Workspace',
  description: 'Manage student details and parent contacts with secure team access, record review, and downloads.',
  openGraph: {
    title: 'LakshyaInstitute',
    description: 'Student details. Parent contacts. One workspace.',
    siteName: 'LakshyaInstitute',
    type: 'website',
    url: '/',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'LakshyaInstitute',
    description: 'Student details. Parent contacts. One workspace.',
    images: ['/opengraph-image'],
  },
  icons: { icon: '/favicon.svg', shortcut: '/favicon.svg' },
};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body className="antialiased">{children}</body></html>}
