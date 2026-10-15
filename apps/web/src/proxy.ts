import { NextResponse, type NextRequest } from "next/server";

// Workspace pages require a session except the guest analysis and guest-result paths.
const PROTECTED_PREFIXES = ["/app"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const sessionToken = request.cookies.get("cgs_session")?.value;
  const guestAnalysisRoute = pathname === "/app/analyze" || /^\/app\/analyses\/[a-f0-9]{32}$/.test(pathname);

  const isProtectedWorkspace = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );

  if (isProtectedWorkspace && !sessionToken && !guestAnalysisRoute) {
    const signInUrl = new URL("/sign-in", request.url);
    signInUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(signInUrl);
  }

  const isSecretAdminGate = process.env.ADMIN_LOGIN_SLUG && pathname === `/admin/${process.env.ADMIN_LOGIN_SLUG}`;
  const isAdminRoute = pathname === "/admin" || pathname.startsWith("/admin/");

  if (isAdminRoute && !isSecretAdminGate && !sessionToken) {
    const signInUrl = new URL("/sign-in", request.url);
    signInUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(signInUrl);
  }

  const response = NextResponse.next();
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  response.headers.set("X-XSS-Protection", "1; mode=block");
  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|cgs-logo.png|world-map.png|fonts).*)",
  ],
};
