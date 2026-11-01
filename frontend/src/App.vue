<script setup lang="ts">
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { api } from "@/api/client";

const route = useRoute();
const router = useRouter();

async function logout() {
  try {
    await api.logout();
  } catch {
    // Cookieが既に無効等でも気にせずログイン画面へ戻す
  } finally {
    router.replace("/");
  }
}
</script>

<template>
  <div class="shell">
    <header v-if="route.name !== 'login'" class="topbar">
      <span class="brand">SSI <em>Spotify Scoring Indicator</em></span>
      <nav>
        <RouterLink to="/battle" :class="{ active: route.name === 'battle' }">対戦</RouterLink>
        <RouterLink to="/rankings" :class="{ active: route.name === 'rankings' }">ランキング</RouterLink>
        <button class="logout-btn" @click="logout">ログアウト</button>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  border-bottom: 1px solid var(--color-border);
}

.brand {
  font-family: var(--font-display);
  font-size: 22px;
  letter-spacing: 0.06em;
}

.brand em {
  font-style: normal;
  color: var(--color-corner-a);
}

nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

nav a {
  text-decoration: none;
  color: var(--color-text-dim);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.03em;
  padding-bottom: 4px;
  border-bottom: 2px solid transparent;
  transition: color 0.15s ease, border-color 0.15s ease;
}

nav a:hover,
nav a.active {
  color: var(--color-text);
  border-color: var(--color-gold);
}

.logout-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-dim);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 600;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.logout-btn:hover {
  border-color: var(--color-corner-a);
  color: var(--color-text);
}

main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
