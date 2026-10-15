import type { NextConfig } from "next";

const configuredApiOrigin = process.env.NEXT_API_ORIGIN;
if (process.env.VERCEL === "1" && !configuredApiOrigin) {
  throw new Error("NEXT_API_ORIGIN must be configured for Vercel deployments.");
}
const apiOrigin = configuredApiOrigin ?? "http://127.0.0.1:8000";
try {
  const parsedApiOrigin = new URL(apiOrigin);
  const isOriginOnly = parsedApiOrigin.pathname === "/" && !parsedApiOrigin.search && !parsedApiOrigin.hash;
  if (!isOriginOnly || parsedApiOrigin.username || parsedApiOrigin.password) {
    throw new Error("NEXT_API_ORIGIN must contain only an API origin, without a path or credentials.");
  }
  if (process.env.VERCEL === "1" && parsedApiOrigin.protocol !== "https:") {
    throw new Error("NEXT_API_ORIGIN must use HTTPS on Vercel.");
  }
} catch (error) {
  if (error instanceof TypeError) {
    throw new Error("NEXT_API_ORIGIN must be an absolute URL.");
  }
  throw error;
}
const developmentEval = process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : "";
const productionHsts = process.env.NODE_ENV === "production"
  ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" }]
  : [];

const nextConfig: NextConfig = {
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Content-Security-Policy", value: `default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline' https://api.fontshare.com; font-src 'self' https://cdn.fontshare.com; script-src 'self' 'unsafe-inline'${developmentEval}; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'` },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
        { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
        { key: "X-DNS-Prefetch-Control", value: "off" },
        { key: "X-Permitted-Cross-Domain-Policies", value: "none" },
        ...productionHsts,
      ],
    }, {
      source: "/admin/:path*",
      headers: [
        { key: "X-Robots-Tag", value: "noindex, nofollow, noarchive" },
        { key: "Cache-Control", value: "private, no-store" },
      ],
    }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
  async redirects() {
    return [
      { source: "/pricing", destination: "/solutions", permanent: true },
      { source: "/usage", destination: "/solutions", permanent: true },
    ];
  },
};

export default nextConfig;
