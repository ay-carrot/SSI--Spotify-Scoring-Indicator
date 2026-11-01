import type {
  CurrentUser,
  MatchResponse,
  MatchResult,
  PairResponse,
  Playlist,
  RankedTrack,
  RankingFilter,
  SyncResult,
} from "@/types";

const BASE_URL = "/api";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    credentials: "include", // httpOnly Cookie(セッション)を送るため必須
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? `リクエストに失敗しました (${res.status})`);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  loginUrl: () => `${BASE_URL}/auth/login`,

  me: () => request<CurrentUser>("/auth/me"),

  logout: () => request<{ detail: string }>("/auth/logout", { method: "POST" }),

  getPlaylists: () => request<Playlist[]>("/library/playlists"),

  syncLibrary: (playlistIds: string[]) =>
    request<SyncResult>("/library/sync", {
      method: "POST",
      body: JSON.stringify({ playlist_ids: playlistIds }),
    }),

  getPair: (playlistId: string) =>
    request<PairResponse>(`/tracks/pair?playlist_id=${encodeURIComponent(playlistId)}`),

  submitMatch: (trackAId: number, trackBId: number, result: MatchResult, playlistId: string) =>
    request<MatchResponse>("/matches", {
      method: "POST",
      body: JSON.stringify({
        playlist_id: playlistId,
        track_a_id: trackAId,
        track_b_id: trackBId,
        result,
      }),
    }),

  getRankings: (playlistId: string, limit = 50, offset = 0) => {
    const params = new URLSearchParams({
      playlist_id: playlistId,
      limit: String(limit),
      offset: String(offset),
    });
    return request<RankedTrack[]>(`/rankings?${params.toString()}`);
  },

  getRankingFilters: () => request<RankingFilter[]>("/rankings/filters"),
};

export { ApiError };
