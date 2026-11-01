<script setup lang="ts">
import type { RankedTrack } from "@/types";

const props = withDefaults(
  defineProps<{
    track: RankedTrack;
    corner?: "a" | "b" | "none";
    clickable?: boolean;
    rank?: number;
    disabled?: boolean;
  }>(),
  {
    corner: "none",
    clickable: false,
    disabled: false,
  }
);

const emit = defineEmits<{ pick: [] }>();

function onClick() {
  if (props.clickable && !props.disabled) emit("pick");
}
</script>

<template>
  <div
    class="card"
    :class="[`corner-${corner}`, { clickable: clickable && !disabled, disabled }]"
    @click="onClick"
  >
    <span v-if="rank" class="rank">#{{ rank }}</span>
    <div class="art-wrap">
      <img v-if="track.image_url" :src="track.image_url" :alt="track.name" class="art" />
      <div v-else class="art art-fallback">♪</div>
    </div>
    <div class="info">
      <p class="name">{{ track.name }}</p>
      <p class="artist">{{ track.artist_name }}</p>
    </div>
    <div class="scoreboard">
      <span class="rating">{{ Math.round(track.rating) }}</span>
      <span class="matches">{{ track.match_count }}戦</span>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  position: relative;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.corner-a {
  border-top: 3px solid var(--color-corner-a);
}

.corner-b {
  border-top: 3px solid var(--color-corner-b);
}

.clickable {
  cursor: pointer;
}

.clickable:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-elevated);
}

.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.rank {
  position: absolute;
  top: 12px;
  left: 14px;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text-dim);
}

.art-wrap {
  width: 100%;
  aspect-ratio: 1 / 1;
  max-width: 220px;
  border-radius: 12px;
  overflow: hidden;
  background: var(--color-surface-raised);
}

.art {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.art-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: var(--color-text-dim);
}

.info {
  text-align: center;
  min-height: 46px;
}

.name {
  margin: 0;
  font-weight: 700;
  font-size: 15px;
  line-height: 1.3;
}

.artist {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-dim);
}

.scoreboard {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-family: var(--font-mono);
}

.rating {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-gold);
}

.matches {
  font-size: 11px;
  color: var(--color-text-dim);
}
</style>
