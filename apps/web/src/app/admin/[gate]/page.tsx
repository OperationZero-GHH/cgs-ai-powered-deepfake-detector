import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { headers } from "next/headers";
import crypto from "node:crypto";
import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = {
  title: "Restricted Operations Gateway · CGS DeepFake Shield",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

function safeCompare(a: string, b: string): boolean {
  if (!a || !b) return false;
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

export default async function AdminLoginPage({ params }: { params: Promise<{ gate: string }> }) {
  const { gate } = await params;
  // Ensure headers are accessed to make the page dynamic and un-cacheable
  await headers();
  const configuredSlug = process.env.ADMIN_LOGIN_SLUG?.trim() ?? "";
  
  if (
    !/^[A-Za-z0-9_-]{32,128}$/.test(configuredSlug) ||
    !safeCompare(gate, configuredSlug)
  ) {
    notFound();
  }
  
  return <AuthForm mode="login" audience="admin" />;
}
