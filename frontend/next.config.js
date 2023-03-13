/** @type {import('next').NextConfig} */
const withImages = require('next-images')

const nextConfig = withImages({
  experimental: {
    appDir: true,
  },
  webpack: (config) => {
    config.experiments.topLevelAwait = true
    return config;
  },
})

module.exports = nextConfig