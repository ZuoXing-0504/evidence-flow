<script setup lang="ts">
import { Database, ExternalLink, FileText, Plus, RefreshCw, Search, Trash2 } from "@lucide/vue"
import { computed, onMounted, ref } from "vue"

import { ApiError, documentsApi } from "@/api"
import AddDocumentDialog from "@/components/AddDocumentDialog.vue"
import AppShell from "@/components/AppShell.vue"
import EmptyState from "@/components/EmptyState.vue"
import StatusPill from "@/components/StatusPill.vue"
import { formatApiDay } from "@/dates"
import type { DocumentRecord } from "@/types"

const documents = ref<DocumentRecord[]>([])
const loading = ref(true)
const creating = ref(false)
const deletingId = ref<string | null>(null)
const dialogOpen = ref(false)
const search = ref("")
const error = ref("")
const dialogError = ref("")

const filtered = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  if (!query) return documents.value
  return documents.value.filter((document) => document.title.toLocaleLowerCase().includes(query))
})

function errorMessage(value: unknown): string {
  return value instanceof ApiError ? value.message : "无法连接知识库服务，请稍后重试"
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ""
  try {
    documents.value = (await documentsApi.list()).items
  } catch (value) {
    error.value = errorMessage(value)
  } finally {
    loading.value = false
  }
}

async function create(title: string, content: string, sourceUri: string | null): Promise<void> {
  creating.value = true
  dialogError.value = ""
  try {
    const document = await documentsApi.create(title, content, sourceUri)
    documents.value.unshift(document)
    dialogOpen.value = false
  } catch (value) {
    dialogError.value = errorMessage(value)
  } finally {
    creating.value = false
  }
}

async function remove(document: DocumentRecord): Promise<void> {
  if (!window.confirm(`确认从知识库中删除“${document.title}”吗？`)) return
  deletingId.value = document.id
  error.value = ""
  try {
    await documentsApi.remove(document.id)
    documents.value = documents.value.filter((item) => item.id !== document.id)
  } catch (value) {
    error.value = errorMessage(value)
  } finally {
    deletingId.value = null
  }
}

onMounted(() => void load())
</script>

<template>
  <AppShell>
    <div class="knowledge-page">
      <header class="page-header">
        <div>
          <p class="eyebrow">本地检索</p>
          <h1>知识库</h1>
          <p>为每个研究任务的 Local Scout 提供私有资料来源。</p>
        </div>
        <button class="text-button primary" type="button" @click="dialogOpen = true">
          <Plus :size="17" /> 添加文档
        </button>
      </header>

      <div v-if="error" class="error-banner">
        <span>{{ error }}</span>
        <button class="icon-button subtle" type="button" title="重试" @click="load"><RefreshCw :size="16" /></button>
      </div>

      <div class="knowledge-toolbar">
        <label class="search-field large"><Search :size="16" /><input v-model="search" type="search" placeholder="搜索文档" /></label>
        <div class="knowledge-stat"><Database :size="16" /><strong>{{ documents.length }}</strong> 篇文档</div>
        <div class="knowledge-stat"><FileText :size="16" /><strong>{{ documents.reduce((sum, item) => sum + item.chunk_count, 0) }}</strong> 个分块</div>
      </div>

      <div v-if="loading" class="document-grid loading-grid"><span v-for="index in 6" :key="index" /></div>
      <EmptyState
        v-else-if="!filtered.length"
        :icon="Database"
        :title="documents.length ? '没有匹配的文档' : '知识库还是空的'"
        :detail="documents.length ? '请尝试其他关键词。' : '添加来源文本，为 Local Scout 提供私有上下文。'"
      >
        <button v-if="!documents.length" class="text-button primary" type="button" @click="dialogOpen = true">添加文档</button>
      </EmptyState>
      <div v-else class="document-grid">
        <article v-for="document in filtered" :key="document.id" class="document-card">
          <header>
            <span class="document-icon"><FileText :size="18" /></span>
            <StatusPill :status="document.status" />
            <button
              class="icon-button subtle danger-icon"
              type="button"
              title="删除文档"
              :disabled="deletingId === document.id"
              @click="remove(document)"
            ><Trash2 :size="16" /></button>
          </header>
          <h2>{{ document.title }}</h2>
          <a v-if="document.source_uri" :href="document.source_uri" target="_blank" rel="noopener noreferrer">
            <ExternalLink :size="14" /> {{ document.source_uri }}
          </a>
          <p v-if="document.error" class="document-error">{{ document.error }}</p>
          <footer>
            <span>{{ document.chunk_count }} 个分块</span>
            <time :datetime="document.created_at">{{ formatApiDay(document.created_at) }}</time>
          </footer>
        </article>
      </div>
    </div>

    <AddDocumentDialog
      :open="dialogOpen"
      :loading="creating"
      :error="dialogError"
      @close="dialogOpen = false"
      @submit="create"
    />
  </AppShell>
</template>
