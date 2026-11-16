<script setup lang="ts">
import {
  BookOpenText,
  Database,
  LogOut,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
} from "@lucide/vue"
import { ref } from "vue"
import { useRouter } from "vue-router"

import { useAuthStore } from "@/stores/auth"

const auth = useAuthStore()
const router = useRouter()
const collapsed = ref(false)

function logout(): void {
  auth.logout()
  void router.push({ name: "login" })
}
</script>

<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': collapsed }">
    <aside class="sidebar">
      <div class="brand-lockup">
        <span class="brand-mark"><Network :size="19" /></span>
        <span class="brand-name">EvidenceFlow</span>
      </div>

      <nav class="primary-nav" aria-label="Primary navigation">
        <RouterLink to="/research" title="Research">
          <BookOpenText :size="19" />
          <span>Research</span>
        </RouterLink>
        <RouterLink to="/knowledge" title="Knowledge base">
          <Database :size="19" />
          <span>Knowledge</span>
        </RouterLink>
      </nav>

      <div class="sidebar-footer">
        <div class="user-summary">
          <span class="avatar">{{ auth.user?.display_name.slice(0, 1).toUpperCase() }}</span>
          <span class="user-copy">
            <strong>{{ auth.user?.display_name }}</strong>
            <small>{{ auth.user?.email }}</small>
          </span>
          <button class="icon-button subtle" type="button" title="Sign out" @click="logout">
            <LogOut :size="17" />
          </button>
        </div>
        <button
          class="collapse-button"
          type="button"
          :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="collapsed = !collapsed"
        >
          <PanelLeftOpen v-if="collapsed" :size="17" />
          <PanelLeftClose v-else :size="17" />
          <span>{{ collapsed ? "Expand" : "Collapse" }}</span>
        </button>
      </div>
    </aside>

    <header class="mobile-header">
      <div class="brand-lockup">
        <span class="brand-mark"><Network :size="18" /></span>
        <span class="brand-name">EvidenceFlow</span>
      </div>
      <button class="icon-button" type="button" title="Sign out" @click="logout">
        <LogOut :size="18" />
      </button>
    </header>

    <main class="app-main">
      <slot />
    </main>

    <nav class="mobile-nav" aria-label="Mobile navigation">
      <RouterLink to="/research"><BookOpenText :size="19" /><span>Research</span></RouterLink>
      <RouterLink to="/knowledge"><Database :size="19" /><span>Knowledge</span></RouterLink>
    </nav>
  </div>
</template>
