<script setup lang="ts">
import { api } from "@/api/client";

function login() {
  window.location.href = api.loginUrl();
}
</script>

<template>
  <div class="hero">
    <h1 class="title">SSI <em>Spotify Scoring Indicator</em></h1>
    <p class="tagline">2曲を比較して楽曲の好みを相対的に算出します</p>

    <button class="cta" @click="login">
      <span class="dot" />
      Spotifyでログインして開始
    </button>

    <div class="rules">
      <div class="rule">
        <span class="num">01</span>
        <p>Spotifyの保存済みライブラリを同期</p>
      </div>
      <div class="rule">
        <span class="num">02</span>
        <p>表示された2曲のうち好きな方を選択</p>
      </div>
      <div class="rule">
        <span class="num">03</span>
        <p>Eloレーティングによりランキングが自動更新</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
  gap: 20px;
}

.bolt {
  font-size: 40px;
  color: var(--color-gold);
}

.title {
  font-size: clamp(48px, 10vw, 96px);
  line-height: 0.95;
}

.title em {
  font-style: normal;
  color: var(--color-corner-a);
}

.tagline {
  color: var(--color-text-dim);
  font-size: 16px;
  max-width: 420px;
  margin: 0;
}

.cta {
  margin-top: 12px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: var(--color-text);
  color: #14141a;
  border: none;
  border-radius: 999px;
  padding: 14px 28px;
  font-size: 15px;
  font-weight: 700;
  transition: transform 0.15s ease;
}

.cta:hover {
  transform: scale(1.04);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #1db954;
}

.rules {
  margin-top: 48px;
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  justify-content: center;
  max-width: 640px;
}

.rule {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 160px;
}

.num {
  font-family: var(--font-mono);
  color: var(--color-corner-b);
  font-size: 13px;
}

.rule p {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-dim);
}
</style>
