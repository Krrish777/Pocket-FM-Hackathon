import type {
  ActRequest,
  ActResponse,
  ApiErrorBody,
  ApiErrorEnvelope,
  Character,
  PlayRequest,
  PlayResponse,
  ReplayAsRequest,
  ReplayResponse,
} from "@/lib/contract";

/**
 * Live client for the turn-loop API, used ONLY by `app/play/page.tsx`.
 *
 * Deliberately separate from `api.ts`'s `CanonClient` — that seam serves the
 * six existing (mock-data) screens against the single-flip divergence
 * contract and must not be touched (see
 * `.superpowers/sdd/demo-path-integration/task-9-report.md` §3). This client
 * goes through the same same-origin proxy (`app/api/[...path]/route.ts`) so
 * there is no CORS to debug, but it addresses the turn-loop backend's actual
 * mount point (`settings.api_v1_str` = `/api/v1`), not the mock's `/api/*`
 * paths used elsewhere in this codebase.
 */

const BASE = "/api/v1";

/** A structured `{error: {...}}` envelope from the backend (see `ApiErrorEnvelope`). */
export class PlayApiError extends Error {
  readonly code: string;
  readonly context?: Record<string, unknown>;

  constructor(body: ApiErrorBody) {
    super(body.message);
    this.name = "PlayApiError";
    this.code = body.code;
    this.context = body.context;
  }
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as { error: unknown }).error === "object" &&
    (value as { error: unknown }).error !== null
  );
}

/** The proxy route's own failure shape (`route.ts`) when the backend is unreachable. */
function isProxyFailure(
  value: unknown,
): value is { error: string; target: string; detail: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as { error?: unknown }).error === "string" &&
    "detail" in value
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  const text = await res.text();
  const data: unknown = text.length > 0 ? JSON.parse(text) : undefined;

  if (!res.ok) {
    if (isApiErrorEnvelope(data)) {
      throw new PlayApiError(data.error);
    }
    if (isProxyFailure(data)) {
      throw new Error(`backend unreachable at ${data.target}: ${data.detail}`);
    }
    throw new Error(`${init?.method ?? "GET"} ${BASE}${path} failed: ${res.status}`);
  }

  return data as T;
}

const post = <T,>(path: string, body: unknown): Promise<T> =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const playApi = {
  getCharacters: (): Promise<Character[]> => request<Character[]>("/characters"),
  play: (body: PlayRequest): Promise<PlayResponse> => post<PlayResponse>("/play", body),
  act: (runId: string, body: ActRequest): Promise<ActResponse> =>
    post<ActResponse>(`/play/${encodeURIComponent(runId)}/act`, body),
  replayAs: (runId: string, body: ReplayAsRequest): Promise<ReplayResponse> =>
    post<ReplayResponse>(`/play/${encodeURIComponent(runId)}/replay-as`, body),
};
