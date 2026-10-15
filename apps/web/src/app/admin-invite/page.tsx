import type { Metadata } from "next";
import { AdminInviteForm } from "@/components/admin-invite-form";

export const metadata: Metadata = {
  title: "Accept administrator invitation",
  robots: { index: false, follow: false, noarchive: true },
  referrer: "no-referrer",
};

export default function AdminInvitePage() {
  return <AdminInviteForm />;
}
