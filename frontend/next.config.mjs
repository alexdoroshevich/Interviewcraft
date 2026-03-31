/** @type {import('next').NextConfig} */
const nextConfig = {
  // Strict mode for catching React issues early
  reactStrictMode: true,
  // Standalone output bundles everything needed for Docker (no node_modules at runtime)
  output: "standalone",
};

export default nextConfig;
