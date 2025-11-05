/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    // Exclude Node.js modules from client-side bundle
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        cluster: false,
        os: false,
        fs: false,
        child_process: false,
        worker_threads: false,
        perf_hooks: false,
        v8: false,
        process: false,
        dgram: false,
        http2: false,
        tls: false,
        net: false,
        async_hooks: false,
      };
      
      // Exclude server-only modules from client bundle
      config.externals = config.externals || [];
      config.externals.push('prom-client');
    }
    return config;
  },
  env: {
    API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8000',
    API_TOKEN: process.env.API_TOKEN || 'dev-token-change-in-production'
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()'
          }
        ]
      }
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_BASE_URL || 'http://localhost:8000'}/:path*`
      }
    ];
  },
  images: {
    domains: []
  },
  typescript: {
    ignoreBuildErrors: false
  },
  eslint: {
    ignoreDuringBuilds: false
  },
  poweredByHeader: false
};

module.exports = nextConfig;
