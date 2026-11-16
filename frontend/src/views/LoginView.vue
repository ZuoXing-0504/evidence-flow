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
        <p class="eyebrow">多 Agent 深度研究工作台</p>
        <h1>让每一个结论，都能追溯到证据。</h1>
        <p>在一个可观测的多 Agent 工作台中完成规划、检索、评审、分析与报告交付。</p>
        <ul>
          <li><Check :size="16" /> 网络与本地知识并行检索</li>
          <li><Check :size="16" /> 引用约束与证据溯源</li>
          <li><Check :size="16" /> 用户隔离的语义记忆</li>
        </ul>
      </div>
      <p class="auth-footnote">为严谨、可复现的研究流程而构建。</p>
    </section>

    <section class="auth-form-section">
      <form class="auth-form" @submit.prevent="submit">
        <header>
          <p class="eyebrow">{{ mode === 'login' ? '欢迎回来' : '创建工作空间' }}</p>
          <h2>{{ mode === "login" ? "登录 EvidenceFlow" : "开始深度研究" }}</h2>
        </header>

        <div class="auth-mode-tabs">
          <button type="button" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
          <button type="button" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        </div>

        <label v-if="mode === 'register'" class="field-label">
          显示名称
          <input v-model="displayName" autocomplete="name" minlength="1" maxlength="120" required />
        </label>
        <label class="field-label">
          邮箱
          <input v-model="email" type="email" autocomplete="email" required />
        </label>
        <label class="field-label">
          密码
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
          {{ auth.loading ? "请稍候" : mode === "login" ? "登录" : "创建账号" }}
          <ArrowRight :size="17" />
        </button>
      </form>
    </section>
  </main>
</template>
