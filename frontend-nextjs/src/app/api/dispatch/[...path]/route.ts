import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const p = await params;
  return proxyRequest(request, p.path);
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const p = await params;
  return proxyRequest(request, p.path);
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const p = await params;
  return proxyRequest(request, p.path);
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const p = await params;
  return proxyRequest(request, p.path);
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const p = await params;
  return proxyRequest(request, p.path);
}

async function proxyRequest(request: NextRequest, path: string[]) {
  const session = await getSession();
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const apiToken = process.env.DISPATCH_API_TOKEN || "";

  const url = new URL(request.url);
  const searchParams = url.searchParams.toString();
  const backendUrl = `${apiBaseUrl}/api/${path.join("/")}${searchParams ? `?${searchParams}` : ""}`;

  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  if (session) {
    headers.set("X-Actor-Id", session.actor_id);
    headers.set("X-Actor-Role", session.actor_role);
  }
  if (apiToken) {
    headers.set("X-API-Token", apiToken);
  }

  const options: RequestInit = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    // Clone the request if we need to read the body multiple times, 
    // though here we only read it once.
    options.body = await request.text();
  }

  try {
    const resp = await fetch(backendUrl, options);
    
    // Check if response is JSON
    const contentType = resp.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      const data = await resp.json();
      return NextResponse.json(data, { status: resp.status });
    } else {
      const text = await resp.text();
      return new NextResponse(text, { 
        status: resp.status,
        headers: { "Content-Type": contentType || "text/plain" }
      });
    }
  } catch (err) {
    console.error("Proxy error:", err);
    return NextResponse.json({ detail: "Backend communication error" }, { status: 502 });
  }
}
