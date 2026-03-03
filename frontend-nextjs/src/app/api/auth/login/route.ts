import { NextRequest, NextResponse } from "next/server";
import { setSession } from "@/lib/session";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { email, password } = body;

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  try {
    const resp = await fetch(`${apiBaseUrl}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    if (resp.ok) {
      const session = await resp.json();
      await setSession(session);
      return NextResponse.json(session);
    } else {
      const error = await resp.json();
      return NextResponse.json(error, { status: resp.status });
    }
  } catch (err) {
    console.error("Login route error:", err);
    return NextResponse.json({ detail: "Internal Server Error" }, { status: 500 });
  }
}
