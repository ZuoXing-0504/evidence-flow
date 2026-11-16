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
  return value instanceof ApiError ? value.message : "The knowledge service could not be reached"
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
  if (!window.confirm(`Remove “${document.title}” from the knowledge base?`)) return
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
          <p class="eyebrow">Local retrieval</p>
          <h1>Knowledge base</h1>
          <p>Private sources available to Local Scout during every research task.</p>
        </div>
        <button class="text-button primary" type="button" @click="dialogOpen = true">
          <Plus :size="17" /> Add document
        </button>
      </header>

      <div v-if="error" class="error-banner">
        <span>{{ error }}</span>
        <button class="icon-button subtle" type="button" title="Retry" @click="load"><RefreshCw :size="16" /></button>
      </div>

      <div class="knowledge-toolbar">
        <label class="search-field large"><Search :size="16" /><input v-model="search" type="search" placeholder="Search documents" /></label>
        <div class="knowledge-stat"><Database :size="16" /><strong>{{ documents.length }}</strong> documents</div>
        <div class="knowledge-stat"><FileText :size="16" /><strong>{{ documents.reduce((sum, item) => sum + item.chunk_count, 0) }}</strong> chunks</div>
      </div>

      <div v-if="loading" class="document-grid loading-grid"><span v-for="index in 6" :key="index" /></div>
      <EmptyState
        v-else-if="!filtered.length"
        :icon="Database"
        :title="documents.length ? 'No matching documents' : 'Your knowledge base is empty'"
        :detail="documents.length ? 'Try another search.' : 'Index source text to give Local Scout private context.'"
      >
        <button v-if="!documents.length" class="text-button primary" type="button" @click="dialogOpen = true">Add document</button>
      </EmptyState>
      <div v-else class="document-grid">
        <article v-for="document in filtered" :key="document.id" class="document-card">
          <header>
            <span class="document-icon"><FileText :size="18" /></span>
            <StatusPill :status="document.status" />
            <button
              class="icon-button subtle danger-icon"
              type="button"
              title="Delete document"
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
            <span>{{ document.chunk_count }} chunks</span>
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
