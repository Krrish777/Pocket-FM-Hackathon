import type { NextRequest } from "next/server";

/**
 * Pass-through proxy to the Python Canon Kernel service.
 *
 * FRONTEND_TECH_STACK.md §0/§5: this exists purely to collapse the frontend and
 * backend onto one origin so there is no CORS to debug on stage, and one
 * `npm run dev` to run. It must contain NO business logic — if you are tempted
 * to reshape a payload here, fix the contract instead (docs/API_CONTRACT_NOTES.md).
 *
 * Inert while NEXT_PUBLIC_USE_MOCK is not "false": the client never calls it.
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/** Hop-by-hop headers that must not be forwarded. */
const STRIPPED = new Set(["host", "connection", "content-length"]);

type Ctx = { params: Promise<{ path: string[] }> };

async function proxy(req: NextRequest, ctx: Ctx): Promise<Response> {
  const { path } = await ctx.params;
  const target = `${BACKEND_URL}/api/${path.join("/")}${new URL(req.url).search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!STRIPPED.has(key.toLowerCase())) headers.set(key, value);
  });

  const hasBody = req.method !== "GET" && req.method !== "HEAD";

  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.text() : undefined,
      cache: "no-store",
    });

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: upstream.headers,
    });
  } catch (error) {
    // Surface an honest, machine-readable failure. Presenter Mode is what keeps
    // this off the projector; swallowing it here would only hide a real outage.
    const detail = error instanceof Error ? error.message : String(error);
    return Response.json(
      { error: "upstream_unreachable", target, detail },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
