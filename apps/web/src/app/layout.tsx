import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import "./theme.css";
import "./auth.css";
import "./account-access.css";
import "./neural-scan.css";
import { CookieBanner } from "@/components/cookie-banner";
import { MotionProvider } from "@/components/motion-provider";
import { AccountAccessProvider } from "@/components/account-access-context";

const poppins = localFont({
  src: [
    { path: "./fonts/Poppins-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/Poppins-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/Poppins-600.woff2", weight: "600", style: "normal" },
    { path: "./fonts/Poppins-700.woff2", weight: "700", style: "normal" },
    { path: "./fonts/Poppins-800.woff2", weight: "800", style: "normal" },
  ],
  variable: "--font-poppins",
  display: "swap",
  fallback: ["sans-serif"],
});

export const metadata: Metadata = {
  title: { default: "CGS DeepFake Shield", template: "%s · CGS DeepFake Shield" },
  description: "Inspect image integrity, metadata, and provenance indicators with clear limitations.",
  icons: {
    icon: "/cgs-logo.png",
    shortcut: "/cgs-logo.png",
    apple: "/cgs-logo.png",
  },
  metadataBase: new URL("https://cgsdeepfakeshield.local"),
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "CGS DeepFake Shield",
    description: "Evidence for review, never a verdict.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "CGS DeepFake Shield",
    description: "Evidence for review, never a verdict.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="light" className={poppins.variable} suppressHydrationWarning>
      <body>
        <AccountAccessProvider>
          <MotionProvider>{children}</MotionProvider>
          <CookieBanner />
        </AccountAccessProvider>
      </body>
    </html>
  );
}
