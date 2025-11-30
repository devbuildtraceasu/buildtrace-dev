/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['storage.googleapis.com', 'buildtrace-storage.storage.googleapis.com'],
    unoptimized: true
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'}/api/:path*`,
      },
      {
        source: '/upload',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'}/upload`,
      },
      {
        source: '/process/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'}/process/:path*`,
      }
    ]
  }
}

module.exports = nextConfig