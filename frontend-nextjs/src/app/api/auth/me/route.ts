import { NextResponse } from "next/server";
import { getSession } from "@/lib/session";

export async function GET() {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  try {
    const resp = await fetch(`${apiBaseUrl}/api/auth/me`, {
      headers: {
        "X-Actor-Id": session.actor_id,
        "X-Actor-Role": session.actor_role,
      },
      cache: "no-store",
    });

    if (!resp.ok) {
      return NextResponse.json(session);
    }

    const data = await resp.json();
    const user = data?.user ?? {};
    const email = user.email || session.email;
    const displayName = user.display_name || session.display_name;
    const avatarUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(
      displayName || email || "User"
    )}&background=0d6efd&color=fff`;

    return NextResponse.json({
      actor_id: session.actor_id,
      actor_role: session.actor_role,
      email,
      display_name: displayName,
      avatar_url: avatarUrl,
      global_role: user.global_role,
    });
  } catch {
    return NextResponse.json(session);
  }
}
