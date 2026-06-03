import type { Metadata, Viewport } from 'next'
import { ClerkProvider } from '@clerk/nextjs'
import { DM_Sans, Instrument_Serif } from 'next/font/google'
import { Providers } from '@/components/layout/Providers'
import './globals.css'

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-dm-sans',
  display: 'swap',
})

const instrumentSerif = Instrument_Serif({
  weight: ['400'],
  style: ['normal', 'italic'],
  subsets: ['latin'],
  variable: '--font-instrument-serif',
  display: 'swap',
})

export const metadata: Metadata = {
  title: {
    template: '%s | LearnOS AI',
    default: 'LearnOS AI — Master Anything. AI Builds The Path.',
  },
  description:
    'AI-powered learning OS that discovers the best resources and builds your personalized curriculum automatically.',
  keywords: ['AI learning', 'personalized curriculum', 'learning roadmap', 'AI tutor', 'online learning'],
  authors: [{ name: 'LearnOS AI' }],
  openGraph: {
    type: 'website',
    title: 'LearnOS AI',
    description: 'Master Anything. AI Builds The Path.',
    siteName: 'LearnOS AI',
  },
  twitter: { card: 'summary_large_image', title: 'LearnOS AI' },
  robots: { index: true, follow: true },
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#faf9f6' },
    { media: '(prefers-color-scheme: dark)', color: '#111111' },
  ],
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        suppressHydrationWarning
        className={`${dmSans.variable} ${instrumentSerif.variable}`}
      >
        <body className="font-sans antialiased">
          <Providers>{children}</Providers>
        </body>
      </html>
    </ClerkProvider>
  )
}
