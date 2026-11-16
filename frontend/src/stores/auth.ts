import { computed, ref } from "vue"
import { defineStore } from "pinia"

import { ApiError, authApi, session } from "@/api"
import type { User } from "@/types"

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const loading = ref(false)
  const isAuthenticated = computed(() => Boolean(user.value && session.get()))

  async function initialize(): Promise<void> {
    if (initialized.value) return
    const accessToken = session.get()
    if (accessToken) {
      try {
        user.value = await authApi.me()
      } catch {
        session.clear()
      }
    }
    initialized.value = true
  }

  async function login(email: string, password: string): Promise<void> {
    loading.value = true
    try {
      const result = await authApi.login(email, password)
      session.set(result.access_token)
      user.value = result.user
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string, displayName: string): Promise<void> {
    loading.value = true
    try {
      const result = await authApi.register(email, password, displayName)
      session.set(result.access_token)
      user.value = result.user
    } finally {
      loading.value = false
    }
  }

  function logout(): void {
    user.value = null
    session.clear()
  }

  function errorMessage(error: unknown): string {
    return error instanceof ApiError ? error.message : "The service could not be reached"
  }

  return {
    user,
    initialized,
    loading,
    isAuthenticated,
    initialize,
    login,
    register,
    logout,
    errorMessage,
  }
})
