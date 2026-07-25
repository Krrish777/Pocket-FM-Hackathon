"use client";

import { useQueries, useQuery } from "@tanstack/react-query";

import {
  mockApi,
  type Moment,
  type RegenerateResult,
  type RippleResult,
  type StoryDetail,
  type StorySummary,
} from "@/lib/mockData";

/**
 * The mock ⇄ live seam.
 *
 * `CanonClient` is the contract from REQUIREMENTS.md §8. Both the mock and the
 * HTTP client implement it identically, so switching the whole app over is a
 * single env flag — no component changes, no call-site edits.
 *
 * See docs/API_CONTRACT_NOTES.md for where our payloads exceed the §8 sketch.
 */
export interface CanonClient {
  getStories(): Promise<StorySummary[]>;
  getStory(storyId: string): Promise<StoryDetail>;
  getMoments(
    storyId: string,
    episodeId: string,
    characterId: string,
  ): Promise<Moment[]>;
  postDivergence(
    storyId: string,
    momentId: string,
    altId: string,
  ): Promise<RippleResult>;
  postRegenerate(rippleId: string): Promise<RegenerateResult>;
  postDefectDemo(): Promise<RegenerateResult>;
}

/** Default is mock: the demo must run with zero backend (REQUIREMENTS.md §10). */
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
  getStories: () => request<StorySummary[]>("/api/stories"),
  getStory: (storyId) =>
    request<StoryDetail>(`/api/stories/${encodeURIComponent(storyId)}`),
  getMoments: (storyId, episodeId, characterId) =>
    request<Moment[]>(
      `/api/stories/${encodeURIComponent(storyId)}/moments` +
        `?episodeId=${encodeURIComponent(episodeId)}` +
        `&characterId=${encodeURIComponent(characterId)}`,
    ),
  postDivergence: (storyId, momentId, altId) =>
    post<RippleResult>("/api/divergence", { storyId, momentId, altId }),
  postRegenerate: (rippleId) =>
    post<RegenerateResult>("/api/regenerate", { rippleId }),
  postDefectDemo: () => post<RegenerateResult>("/api/demo/defect", {}),
};

/**
 * `mockApi.getMoments` takes (episodeId, characterId); the real endpoint is
 * scoped by story. We adapt rather than widen the mock, so `mockData.ts` stays
 * a verbatim copy of the authored seed data.
 */
const mockClient: CanonClient = {
  getStories: () => mockApi.getStories(),
  getStory: (storyId) => mockApi.getStory(storyId),
  getMoments: (_storyId, episodeId, characterId) =>
    mockApi.getMoments(episodeId, characterId),
  postDivergence: (storyId, momentId, altId) =>
    mockApi.postDivergence(storyId, momentId, altId),
  postRegenerate: (rippleId) => mockApi.postRegenerate(rippleId),
  postDefectDemo: () => mockApi.postDefectDemo(),
};

export const client: CanonClient = USE_MOCK ? mockClient : httpClient;

/* ── Hooks ──────────────────────────────────────────────────────────────
   Divergence and regeneration are modelled as QUERIES, not mutations, even
   though they are POSTs. They are pure functions of their inputs, so caching
   them by input means a result computed once survives every screen change —
   no recompute, no second spinner, no dead air if the operator steps back
   mid-demo. That is exactly the "pre-cache the rehearsed path" requirement.
   --------------------------------------------------------------------- */

export function useStories() {
  return useQuery({ queryKey: ["stories"], queryFn: () => client.getStories() });
}

export function useStory(storyId: string | null) {
  return useQuery({
    queryKey: ["story", storyId],
    queryFn: () => client.getStory(storyId!),
    enabled: Boolean(storyId),
  });
}

export function useMoments(
  storyId: string | null,
  episodeId: string | null,
  characterId: string | null,
) {
  return useQuery({
    queryKey: ["moments", storyId, episodeId, characterId],
    queryFn: () => client.getMoments(storyId!, episodeId!, characterId!),
    enabled: Boolean(storyId && episodeId && characterId),
  });
}

/**
 * Which of a character's episodes actually hold an authored divergence point.
 *
 * Only a couple of moments are authored, so highlighting every episode the
 * character appears in would produce clicks that lead nowhere. Rather than
 * writing an empty state to explain that — REQUIREMENTS.md §3 forbids exactly
 * that — we resolve moments up front and make unauthored episodes inert.
 *
 * The query keys match `useMoments` exactly, so the Divergence screen reads
 * straight from this cache instead of refetching.
 */
export function useEpisodesWithMoments(
  storyId: string | null,
  characterId: string | null,
  episodeIds: string[],
) {
  const results = useQueries({
    queries: episodeIds.map((episodeId) => ({
      queryKey: ["moments", storyId, episodeId, characterId],
      queryFn: () => client.getMoments(storyId!, episodeId, characterId!),
      enabled: Boolean(storyId && characterId),
      staleTime: Infinity,
    })),
  });

  // Hand back the moments themselves, not just which episodes have them: the
  // timeline needs a momentId the instant an episode is clicked, and refetching
  // there would cost the operator a second click mid-demo.
  const momentsByEpisode = new Map<string, Moment[]>();
  episodeIds.forEach((episodeId, i) => {
    const moments = results[i]?.data;
    if (moments?.length) momentsByEpisode.set(episodeId, moments);
  });

  return {
    momentsByEpisode,
    withMoments: new Set(momentsByEpisode.keys()),
    resolved: results.every((r) => !r.isPending),
  };
}

export function useDivergence(
  storyId: string | null,
  momentId: string | null,
  altId: string | null,
) {
  return useQuery({
    queryKey: ["divergence", storyId, momentId, altId],
    queryFn: () => client.postDivergence(storyId!, momentId!, altId!),
    enabled: Boolean(storyId && momentId && altId),
  });
}

export function useRegenerate(rippleId: string | null) {
  return useQuery({
    queryKey: ["regenerate", rippleId],
    queryFn: () => client.postRegenerate(rippleId!),
    enabled: Boolean(rippleId),
  });
}

export function useDefectDemo(enabled: boolean) {
  return useQuery({
    queryKey: ["defect"],
    queryFn: () => client.postDefectDemo(),
    enabled,
  });
}
