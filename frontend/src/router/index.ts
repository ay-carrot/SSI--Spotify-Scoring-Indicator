import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
    },
    {
      path: "/battle",
      name: "battle",
      component: () => import("@/views/BattleView.vue"),
    },
    {
      path: "/rankings",
      name: "rankings",
      component: () => import("@/views/RankingsView.vue"),
    },
  ],
});

export default router;
