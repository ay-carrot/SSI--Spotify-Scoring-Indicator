<script setup lang="ts">
import type { Playlist } from "@/types";

const props = defineProps<{
  playlists: Playlist[];
  selectedIds: string[];
}>();

const emit = defineEmits<{
  "update:selectedIds": [string[]];
}>();

function toggle(id: string) {
  const next = props.selectedIds.includes(id)
    ? props.selectedIds.filter((x) => x !== id)
    : [...props.selectedIds, id];
  emit("update:selectedIds", next);
}
</script>

<template>
  <div class="picker">
    <p class="hint">対戦を行うプレイリストを選んでください</p>
    <ul class="list">
      <li
        v-for="p in playlists"
        :key="p.id"
        class="item"
        :class="{ checked: selectedIds.includes(p.id) }"
        @click="toggle(p.id)"
      >
        <span class="checkbox" aria-hidden="true" />
        <img v-if="p.image_url" :src="p.image_url" :alt="p.name" class="thumb" />
        <div v-else class="thumb thumb-fallback">♪</div>
        <div class="meta">
          <p class="name">{{ p.name }}</p>
          <p class="count">{{ p.track_count }}曲</p>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.picker {
  width: 100%;
  max-width: 480px;
}

.hint {
  color: var(--color-text-dim);
  font-size: 13px;
  margin: 0 0 12px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 360px;
  overflow-y: auto;
}

.item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 8px 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.item:hover {
  border-color: var(--color-text-dim);
}

.item.checked {
  border-color: var(--color-gold);
  background: var(--color-surface-raised);
}

.checkbox {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 2px solid var(--color-text-dim);
  flex-shrink: 0;
}

.item.checked .checkbox {
  background: var(--color-gold);
  border-color: var(--color-gold);
}

.thumb {
  width: 36px;
  height: 36px;
  border-radius: 6px;
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
  min-width: 0;
}

.name {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.count {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--color-text-dim);
}
</style>
