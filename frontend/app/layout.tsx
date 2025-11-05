import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import '../styles/metrics-dashboard.css';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans'
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono'
});

export const metadata: Metadata = {
  title: 'Adelaide Weather Forecasting System',
  description:
    'Production-ready analog ensemble weather forecasting with uncertainty quantification',
  keywords: [
    'weather',
    'forecasting',
    'Adelaide',
    'analog ensemble',
    'uncertainty quantification'
  ],
  authors: [{ name: 'Adelaide Weather Forecasting Team' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#0A0D12',
  robots: 'noindex, nofollow', // Private system
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png'
  },
  openGraph: {
    title: 'Adelaide Weather Forecasting System',
    description: 'Production-ready analog ensemble weather forecasting',
    type: 'website',
    locale: 'en_AU'
  }
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang='en' className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <meta name='color-scheme' content='dark' />
      </head>
      <body className='font-sans antialiased'>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
