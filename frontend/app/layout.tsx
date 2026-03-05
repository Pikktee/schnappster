import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import { Toaster } from 'sonner'
import './globals.css'

const _inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: 'Schnappster',
  description: 'Dein persoenlicher Schnaeppchen-Finder fuer Kleinanzeigen.de',
}

export const viewport: Viewport = {
  themeColor: '#F59E0B',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="de">
      <body className="font-sans antialiased">
        {children}
        <Toaster position="top-right" richColors />
      </body>
    </html>
  )
}
