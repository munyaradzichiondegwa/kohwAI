const withPWA = require('next-pwa')({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
  runtimeCaching: [
    // NOTE: API responses are deliberately NOT cached by the service worker. They are authenticated personal data
    // (a shared phone would leak one farmer's records to the next), and the app keeps its own offline copy of the
    // few things that need it in IndexedDB (lib/offline.ts). The old rule here was also unreachable: a `^`-anchored
    // regex never matches Workbox's full-URL string.
    {
      urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/,
      handler: 'CacheFirst',
      options: { cacheName: 'image-cache', expiration: { maxEntries: 200, maxAgeSeconds: 7 * 24 * 60 * 60 } },
    },
  ],
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',   // '' = same origin (production)
    NEXT_PUBLIC_WS_URL:  process.env.NEXT_PUBLIC_WS_URL  ?? 'ws://localhost:8000',
  },
};

module.exports = withPWA(nextConfig);
