import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function resolveBackendBaseUrl(): string {
  if (process.env.BACKEND_INTERNAL_URL) {
    return process.env.BACKEND_INTERNAL_URL.replace(/\/+$/, "");
  }
  if (process.env.RENDER_BACKEND_HOST) {
    const host = process.env.RENDER_BACKEND_HOST.replace(/^https?:\/\//, "").replace(/\/+$/, "");
    return `https://${host}`;
  }
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/?$/, "").replace(/\/+$/, "");
  }
  return "http://127.0.0.1:8000";
}

async function proxyRequest(
  request: NextRequest,
  context: { params: { path: string[] } }
): Promise<NextResponse> {
  const path = (context.params?.path || []).join("/");
  const search = request.nextUrl.search || "";
  const targetUrl = `${resolveBackendBaseUrl()}/api/${path}${search}`;

  const forwardHeaders = new Headers();
  const allowedRequestHeaders = ["authorization", "content-type", "accept", "x-request-id"];
  for (const name of allowedRequestHeaders) {
    const val = request.headers.get(name);
    if (val) forwardHeaders.set(name, val);
  }

  const method = request.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  try {
    let upstream: Response | null = null;
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        upstream = await fetch(targetUrl, {
          method,
          headers: forwardHeaders,
          body: hasBody && body && body.byteLength > 0 ? body : undefined,
          redirect: "manual",
          signal: AbortSignal.timeout(90000),
        });
        if (upstream.status !== 502 && upstream.status !== 503) {
          break;
        }
      } catch (innerErr) {
        if (attempt === 1) throw innerErr;
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    if (!upstream) {
      throw new Error("Empty upstream response");
    }

    const responseHeaders = new Headers();
    const contentType = upstream.headers.get("content-type");
    if (contentType) responseHeaders.set("content-type", contentType);
    const requestId = upstream.headers.get("x-request-id");
    if (requestId) responseHeaders.set("x-request-id", requestId);

    const payload = upstream.status === 204 ? null : await upstream.arrayBuffer();
    return new NextResponse(payload, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: `Backend service unreachable via proxy (${err?.message || "network error"}).` },
      { status: 502 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
export const OPTIONS = proxyRequest;
