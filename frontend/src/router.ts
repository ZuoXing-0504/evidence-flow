import { createRouter, createWebHistory } from "vue-router"

import { useAuthStore } from "@/stores/auth"
import KnowledgeView from "@/views/KnowledgeView.vue"
import LoginView from "@/views/LoginView.vue"
import ResearchView from "@/views/ResearchView.vue"

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/", redirect: "/research" },
    { path: "/research", name: "research", component: ResearchView },
    { path: "/knowledge", name: "knowledge", component: KnowledgeView },
    { path: "/:pathMatch(.*)*", redirect: "/research" },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()
  if (!to.meta.public && !auth.isAuthenticated) return { name: "login" }
  if (to.name === "login" && auth.isAuthenticated) return { name: "research" }
  return true
})

export default router
