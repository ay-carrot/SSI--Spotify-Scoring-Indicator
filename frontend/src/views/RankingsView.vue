<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import { api, ApiError } from "@/api/client";
import type { RankedTrack, RankingFilter } from "@/types";

const tracks = ref<RankedTrack[]>([]);
const filters = ref<RankingFilter[]>([]);
const selectedPlaylistId = ref<string | null>(null);

const loading = ref(false);
const errorMessage = ref<string | null>(null);

async function loadFilters() {
  try {
    filters.value = await api.getRankingFilters();
    if (!selectedPlaylistId.value) {
      selectedPlaylistId.value = filters.value[0]?.playlist_id ?? null;
    }
  } catch {
    // 絞り込み選択肢の取得に失敗した場合は何も表示できない
  }
}

async function loadRankings() {
  if (!selectedPlaylistId.value) {
    tracks.value = [];
    return;
  }
  loading.value = true;
  errorMessage.value = null;
  try {
    tracks.value = await api.getRankings(selectedPlaylistId.value, 100, 0);
  } catch (e) {
    errorMessage.value = e instanceof ApiError ? e.message : "ランキングの取得に失敗しました。";
  } finally {
    loading.value = false;
  }
}

watch(selectedPlaylistId, () => loadRankings());

onMounted(async () => {
  await loadFilters();
  await loadRankings();
});
</script>

<template>
  <div class="rankings">
    <div class="header-row">
      <h2 class="heading">RANKINGS</h2>
      <select v-if="filters.length > 0" v-model="selectedPlaylistId" class="filter-select">
        <option v-for="f in filters" :key="f.playlist_id" :value="f.playlist_id">
          {{ f.playlist_name }}（{{ f.track_count }}曲）
        </option>
      </select>
    </div>

    <p v-if="errorMessage" class="notice-error">{{ errorMessage }}</p>
    <div v-if="loading" class="loading">読み込み中...</div>

    <ol v-else class="list">
      <li v-for="(track, i) in tracks" :key="track.id" class="row">
        <span class="rank" :class="{ top: i < 3 }">{{ i + 1 }}</span>
        <img v-if="track.image_url" :src="track.image_url" :alt="track.name" class="thumb" />
        <div v-else class="thumb thumb-fallback">♪</div>
        <div class="meta">
          <p class="name">{{ track.name }}</p>
          <p class="artist">{{ track.artist_name }}</p>
        </div>
        <span class="rating">{{ Math.round(track.rating) }}</span>
        <span class="matches">{{ track.match_count }}戦</span>
      </li>
    </ol>

    <p v-if="!loading && filters.length === 0" class="empty">
      まだ対戦データがありません。「対戦」タブから曲を比較してみましょう。
    </p>
    <p v-else-if="!loading && tracks.length === 0" class="empty">
      このプールにはまだランキングデータがありません。
    </p>
  </div>
</template>

<style scoped>
.rankings {
  flex: 1;
  padding: 40px 20px;
  max-width: 720px;
  margin: 0 auto;
  width: 100%;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 24px;
}

.heading {
  font-size: 32px;
  margin: 0;
  color: var(--color-gold);
}

.filter-select {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-body);
}

.loading,
.empty {
  color: var(--color-text-dim);
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 10px 16px;
}

.rank {
  font-family: var(--font-mono);
  width: 28px;
  text-align: right;
  color: var(--color-text-dim);
}

.rank.top {
  color: var(--color-gold);
  font-weight: 700;
}

.thumb {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
}

.thumb-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-raised);
  color: var(--color-text-dim);
}

.meta {
  flex: 1;
  min-width: 0;
}

.name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.artist {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--color-text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rating {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--color-gold);
  min-width: 48px;
  text-align: right;
}

.matches {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
  min-width: 40px;
  text-align: right;
}
</style>
