<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api, ApiError } from "@/api/client";
import PlaylistPicker from "@/components/PlaylistPicker.vue";
import TrackCard from "@/components/TrackCard.vue";
import type { MatchResult, PairResponse, Playlist, RankingFilter } from "@/types";

const route = useRoute();
const router = useRouter();

const pair = ref<PairResponse | null>(null);
const playlists = ref<Playlist[]>([]);
const selectedIds = ref<string[]>(["liked_songs"]);

// 対戦は常に1プール(プレイリスト)単位で行う。
const pools = ref<RankingFilter[]>([]);
const currentPoolId = ref<string | null>(null);
const loadingPools = ref(false);

const loadingPair = ref(false);
const loadingPlaylists = ref(false);
const submitting = ref(false);
const syncing = ref(false);
const showPicker = ref(false);

const errorMessage = ref<string | null>(null);
const syncMessage = ref<string | null>(null);
const totalMatches = ref(0);

async function ensureAuthed() {
  try {
    await api.me();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      router.replace("/");
    }
  }
}

async function loadPlaylists() {
  loadingPlaylists.value = true;
  try {
    playlists.value = await api.getPlaylists();
  } catch (e) {
    errorMessage.value = e instanceof ApiError ? e.message : "プレイリストの取得に失敗しました。";
  } finally {
    loadingPlaylists.value = false;
  }
}

async function loadPools(preferPoolId?: string) {
  loadingPools.value = true;
  try {
    pools.value = await api.getRankingFilters();
  } catch {
    // プール一覧の取得に失敗しても、後続の同期を促す表示は出せる
  } finally {
    loadingPools.value = false;
  }

  const stillExists = pools.value.some((p) => p.playlist_id === currentPoolId.value);
  if (preferPoolId && pools.value.some((p) => p.playlist_id === preferPoolId)) {
    currentPoolId.value = preferPoolId;
  } else if (!stillExists) {
    currentPoolId.value = pools.value[0]?.playlist_id ?? null;
  }
}

async function loadPair() {
  if (!currentPoolId.value) {
    pair.value = null;
    showPicker.value = true;
    return;
  }
  loadingPair.value = true;
  errorMessage.value = null;
  try {
    pair.value = await api.getPair(currentPoolId.value);
  } catch (e) {
    pair.value = null;
    if (e instanceof ApiError && e.status === 400) {
      // このプールに対戦できる曲がまだ無い -> プレイリスト選択を開く
      showPicker.value = true;
    } else {
      errorMessage.value =
        e instanceof ApiError ? e.message : "対戦カードの取得に失敗しました。時間をおいて再試行してください。";
    }
  } finally {
    loadingPair.value = false;
  }
}

async function onPoolChange() {
  await loadPair();
}

async function syncSelected() {
  if (selectedIds.value.length === 0) {
    errorMessage.value = "同期するプレイリストを1つ以上選んでください。";
    return;
  }
  syncing.value = true;
  syncMessage.value = null;
  errorMessage.value = null;
  try {
    const result = await api.syncLibrary(selectedIds.value);
    syncMessage.value = `同期完了: ${result.fetched}曲取得 / 新規${result.created}曲`;
    if (result.skipped_playlist_ids.length > 0) {
      syncMessage.value += `（取得できなかったプレイリストが${result.skipped_playlist_ids.length}件あります。Spotifyのおまかせ系プレイリストは取得できないことがあります）`;
    }
    showPicker.value = false;
    // 単体のプレイリストを同期した場合は、そのプールを対戦対象として選択する
    const preferPoolId = selectedIds.value.length === 1 ? selectedIds.value[0] : undefined;
    await loadPools(preferPoolId);
    await loadPair();
  } catch (e) {
    errorMessage.value = e instanceof ApiError ? e.message : "ライブラリの同期に失敗しました。";
  } finally {
    syncing.value = false;
  }
}

async function pick(trackAId: number, trackBId: number, result: MatchResult) {
  if (submitting.value || !currentPoolId.value) return;
  submitting.value = true;
  try {
    await api.submitMatch(trackAId, trackBId, result, currentPoolId.value);
    totalMatches.value += 1;
    await loadPair();
  } catch (e) {
    errorMessage.value = e instanceof ApiError ? e.message : "結果の送信に失敗しました。";
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  await ensureAuthed();
  await loadPlaylists();
  await loadPools();

  // ログイン直後(バックエンドが /battle?sync=1 でリダイレクトしてくる)は、
  // 毎回プレイリスト選択パネルを開く。
  if (route.query.sync !== undefined) {
    showPicker.value = true;
    // 一度開いたらURLからsyncフラグを消しておく(リロード時に毎回開かないように)
    router.replace({ path: "/battle" });
  }

  await loadPair();
});
</script>

<template>
  <div class="battle">
    <div class="toolbar">
      <button class="ghost-btn" @click="showPicker = !showPicker">
        {{ showPicker ? "閉じる" : "プレイリストを選ぶ" }}
      </button>

      <label v-if="pools.length > 0" class="pool-select-label">
        対戦プール:
        <select v-model="currentPoolId" class="pool-select" @change="onPoolChange">
          <option v-for="p in pools" :key="p.playlist_id" :value="p.playlist_id">
            {{ p.playlist_name }}（{{ p.track_count }}曲）
          </option>
        </select>
      </label>

      <span class="counter">今回のセッション: {{ totalMatches }}戦</span>
    </div>

    <div v-if="showPicker" class="picker-panel">
      <PlaylistPicker
        v-if="!loadingPlaylists"
        :playlists="playlists"
        :selected-ids="selectedIds"
        @update:selected-ids="(v) => (selectedIds = v)"
      />
      <p v-else class="loading">プレイリストを読み込み中...</p>
      <button class="sync-btn" :disabled="syncing" @click="syncSelected">
        {{ syncing ? "同期中..." : "選択したプレイリストを同期" }}
      </button>
    </div>

    <p v-if="syncMessage" class="notice notice-ok">{{ syncMessage }}</p>
    <p v-if="errorMessage" class="notice notice-error">{{ errorMessage }}</p>

    <div v-if="loadingPair || loadingPools" class="loading">対戦カードを準備中...</div>

    <template v-else-if="pair">
      <div class="arena">
        <TrackCard
          :track="pair.track_a"
          corner="a"
          clickable
          :disabled="submitting"
          @pick="pick(pair!.track_a.id, pair!.track_b.id, 'a_win')"
        />
        <div class="vs-col">
          <span class="vs">VS</span>
          <button
            class="draw-btn"
            :disabled="submitting"
            @click="pick(pair!.track_a.id, pair!.track_b.id, 'draw')"
          >
            引き分け
          </button>
        </div>
        <TrackCard
          :track="pair.track_b"
          corner="b"
          clickable
          :disabled="submitting"
          @pick="pick(pair!.track_a.id, pair!.track_b.id, 'b_win')"
        />
      </div>
    </template>

    <div v-else-if="!showPicker" class="empty">
      <p>対戦できる曲がまだありません。「プレイリストを選ぶ」から同期してください。</p>
    </div>
  </div>
</template>

<style scoped>
.battle {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  gap: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  gap: 16px;
}

.ghost-btn,
.sync-btn {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  border-radius: 999px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  transition: border-color 0.15s ease;
}

.ghost-btn:hover,
.sync-btn:hover:not(:disabled) {
  border-color: var(--color-gold);
}

.sync-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.pool-select-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-dim);
}

.pool-select {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-body);
}

.counter {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-dim);
}

.picker-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: 20px;
}

.notice {
  font-size: 13px;
  margin: 0;
}

.notice-ok {
  color: var(--color-corner-b);
}

.notice-error {
  color: var(--color-corner-a);
}

.loading,
.empty {
  color: var(--color-text-dim);
  padding: 40px 0;
}

.arena {
  display: flex;
  align-items: center;
  gap: 28px;
  flex-wrap: wrap;
  justify-content: center;
}

.arena > :deep(.card) {
  width: 260px;
}

.vs-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.vs {
  font-family: var(--font-display);
  font-size: 40px;
  color: var(--color-gold);
  transform: rotate(-6deg);
  display: inline-block;
}

.draw-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-dim);
  border-radius: 999px;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.draw-btn:hover:not(:disabled) {
  border-color: var(--color-text-dim);
  color: var(--color-text);
}

.draw-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

@media (max-width: 640px) {
  .vs {
    transform: rotate(0deg);
  }
}
</style>
