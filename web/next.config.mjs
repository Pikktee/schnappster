/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Static export only for production build (FastAPI serves web/out). Omit in dev so dynamic routes work on localhost:3000.
  ...(process.env.NODE_ENV === "production" && { output: "export" }),
  trailingSlash: true,
}

export default nextConfig
