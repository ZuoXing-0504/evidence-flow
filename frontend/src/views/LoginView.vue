<script setup lang="ts">
import { ArrowRight, Check, Network } from "@lucide/vue"
import { ref } from "vue"
import { useRouter } from "vue-router"

import { useAuthStore } from "@/stores/auth"

const auth = useAuthStore()
const router = useRouter()
const mode = ref<"login" | "register">("login")
const email = ref("")
const password = ref("")
const displayName = ref("")
const error = ref("")

async function submit(): Promise<void> {
  error.value = ""
  try {
    if (mode.value === "login") await auth.login(email.value, password.value)
    else await auth.register(email.value, password.value, displayName.value)
    await router.push({ name: "research" })
  } catch (value) {
    error.value = auth.errorMessage(value)
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-intro">
      <div class="auth-brand"><span class="brand-mark"><Network :size="21" /></span>EvidenceFlow</div>
      <div class="auth-intro-copy">
        <p class="eyebrow">Deep research workbench</p>
        <h1>Trace every conclusion back to evidence.</h1>
        <p>Plan, search, judge, analyze, and publish from one observable multi-agent workspace.</p>
        <ul>
          <li><Check :size="16" /> Parallel web and local knowledge retrieval</li>
          <li><Check :size="16" /> Citation-constrained reports</li>
          <li><Check :size="16" /> User-scoped semantic memory</li>
        </ul>
      </div>
      <p class="auth-footnote">Built for rigorous, repeatable research.</p>
    </section>

    <section class="auth-form-section">
      <form class="auth-form" @submit.prevent="submit">
        <header>
          <p class="eyebrow">{{ mode === 'login' ? 'Welcome back' : 'Create workspace' }}</p>
          <h2>{{ mode === "login" ? "Sign in to EvidenceFlow" : "Start researching" }}</h2>
        </header>

        <div class="auth-mode-tabs">
          <button type="button" :class="{ active: mode === 'login' }" @click="mode = 'login'">Sign in</button>
          <button type="button" :class="{ active: mode === 'register' }" @click="mode = 'register'">Register</button>
        </div>

        <label v-if="mode === 'register'" class="field-label">
          Display name
          <input v-model="displayName" autocomplete="name" minlength="1" maxlength="120" required />
        </label>
        <label class="field-label">
          Email
          <input v-model="email" type="email" autocomplete="email" required />
        </label>
        <label class="field-label">
          Password
          <input
            v-model="password"
            type="password"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            :minlength="mode === 'register' ? 8 : 1"
            maxlength="128"
            required
          />
        </label>

        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="auth-submit" type="submit" :disabled="auth.loading">
          {{ auth.loading ? "Please wait" : mode === "login" ? "Sign in" : "Create account" }}
          <ArrowRight :size="17" />
        </button>
      </form>
    </section>
  </main>
</template>
