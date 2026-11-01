export interface RankedTrack {
  id: number;
  spotify_track_id: string;
  name: string;
  artist_name: string;
  image_url: string | null;
  rating: number;
  match_count: number;
}

export interface PairResponse {
  track_a: RankedTrack;
  track_b: RankedTrack;
}

export type MatchResult = "a_win" | "b_win" | "draw";

export interface MatchResponse {
  track_a: RankedTrack;
  track_b: RankedTrack;
  result: MatchResult;
}

export interface Playlist {
  id: string;
  name: string;
  image_url: string | null;
  track_count: number;
  is_liked_songs: boolean;
}

export interface SyncResult {
  fetched: number;
  created: number;
  updated: number;
  skipped_playlist_ids: string[];
}

export interface RankingFilter {
  playlist_id: string;
  playlist_name: string;
  track_count: number;
}

export interface CurrentUser {
  id: number;
  spotify_user_id: string;
  display_name: string | null;
  email: string | null;
}
