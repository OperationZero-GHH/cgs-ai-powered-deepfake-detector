import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AuthGuard } from "@/components/auth-guard";
import AdminContent from "./admin-content";

const apiOrigin = process.env.NEXT_API_ORIGIN ?? "http://127.0.0.1:8000";

function adminLoginPath() {
  const configuredSlug = process.env.ADMIN_LOGIN_SLUG?.trim() ?? "";
  return /^[A-Za-z0-9_-]{32,128}$/.test(configuredSlug) ? `/admin/${configuredSlug}` : "/sign-in";
}

export default async function AdminPage() {
  const token = (await cookies()).get("cgs_session")?.value;
  if (!token) redirect(adminLoginPath());

  let response: Response;
  try {
    response = await fetch(`${apiOrigin}/api/v1/auth/me`, {
      headers: { cookie: `cgs_session=${token}` },
      cache: "no-store",
    });
  } catch {
    return (
      <section className="panel">
        <h1>Admin overview unavailable</h1>
        <p role="alert">The account service could not be reached. Try again when the API is available.</p>
      </section>
    );
  }

  if (response.status === 401) redirect(adminLoginPath());
  if (!response.ok) {
    return (
      <section className="panel">
        <h1>Admin overview unavailable</h1>
        <p role="alert">The account service could not verify access. Try again later.</p>
      </section>
    );
  }

  const user: { role: string } = await response.json();
  if (user.role !== "admin") redirect("/app");

  return (
    <AuthGuard admin={true}>
      <AdminContent />
    </AuthGuard>
  );
}
