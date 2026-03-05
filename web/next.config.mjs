/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Static export so FastAPI can serve the prebuilt app from web/out
  output: "export",
  trailingSlash: true,
}

export default nextConfig
