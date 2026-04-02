/** @type {import('next').NextConfig} */
const nextConfig = {
  // Strict mode for catching React issues early
  reactStrictMode: true,
  // Standalone bundles everything for Docker. Vercel has its own build system
  // and breaks with standalone mode — skip it when VERCEL=1 is set.
  output: process.env.VERCEL ? undefined : "standalone",
};

export default nextConfig;
