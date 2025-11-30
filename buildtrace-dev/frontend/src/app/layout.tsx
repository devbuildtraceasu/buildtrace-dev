import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'BuildTrace',
  description: 'AI-powered architectural drawing comparison and analysis',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

