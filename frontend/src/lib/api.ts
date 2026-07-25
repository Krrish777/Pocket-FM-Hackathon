"use client";

import { useQuery } from "@tanstack/react-query";

import {
  mockApi,
  type Character,
  type CharacterId,
  type FactDelta,
  type LocalizedText,
  type Run,
  type Story,
  type VerifierResult,
} from "@/lib/mockData";

/**
 * The mock ⇄ live seam.
 *
 * `CanonClient` is the contract for this build (see `docs/API_CONTRACT_NOTES.md`
 * for the full shape and what changed from the prior single-flip contract).
 * Both the mock and the HTTP client implement it identically, so switching the
 * whole app over is a single env flag — no component changes, no call-site edits.
 */
export interface CanonClient {
  getStories(): Promise<Story[]>;
  getCharacters(): Promise<Character[]>;
  getRun(protagonistId: CharacterId): Promise<Run>;
  postChoice(runId: string, turnIndex: number, choiceId: string): Promise<{ delta: FactDelta }>;
  postDefectDemo(): Promise<{ sceneText: LocalizedText; verifier: VerifierResult }>;
}

/** Default is mock: the demo must run with zero backend. */
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

const post = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

/** Hits the Route Handler proxy at /api/* — same origin, so no CORS. */
const httpClient: CanonClient = {
  getStories: () => request<Story[]>("/api/stories"),
  getCharacters: () => request<Character[]>("/api/characters"),
  getRun: (protagonistId) =>
    request<Run>(`/api/runs/${encodeURIComponent(protagonistId)}`),
  postChoice: (runId, turnIndex, choiceId) =>
    post<{ delta: FactDelta }>(`/api/turns/${encodeURIComponent(runId)}/${turnIndex}/choice`, { choiceId }),
  postDefectDemo: () =>
    post<{ sceneText: LocalizedText; verifier: VerifierResult }>("/api/demo/defect", {}),
};

const mockClient: CanonClient = {
  getStories: () => mockApi.getStories(),
  getCharacters: () => mockApi.getCharacters(),
  getRun: (protagonistId) => mockApi.getRun(protagonistId),
  postChoice: (runId, turnIndex, choiceId) => mockApi.postChoice(runId, turnIndex, choiceId),
  postDefectDemo: () => mockApi.postDefectDemo(),
};

export const client: CanonClient = USE_MOCK ? mockClient : httpClient;

/* ── Hooks ──────────────────────────────────────────────────────────────
   The run is a QUERY, cached by protagonist, so it survives every screen
   change with no recompute — the rehearsed path is fetched once. A per-turn
   choice is also cached by its full key, so stepping back and forward through
   the demo (e.g. presenter recovering mid-run) never returns a different
   ripple for the same input.
   --------------------------------------------------------------------- */

export function useStories() {
  return useQuery({ queryKey: ["stories"], queryFn: () => client.getStories() });
}

export function useCharacters() {
  return useQuery({ queryKey: ["characters"], queryFn: () => client.getCharacters() });
}

export function useRun(protagonistId: CharacterId | null) {
  return useQuery({
    queryKey: ["run", protagonistId],
    queryFn: () => client.getRun(protagonistId!),
    enabled: Boolean(protagonistId),
    staleTime: Infinity,
  });
}

export function useChoice(runId: string | null, turnIndex: number | null, choiceId: string | null) {
  return useQuery({
    queryKey: ["choice", runId, turnIndex, choiceId],
    queryFn: () => client.postChoice(runId!, turnIndex!, choiceId!),
    enabled: Boolean(runId && turnIndex && choiceId),
    staleTime: Infinity,
  });
}

export function useDefectDemo(enabled: boolean) {
  return useQuery({
    queryKey: ["defect"],
    queryFn: () => client.postDefectDemo(),
    enabled,
  });
}
