<script setup lang="ts">
import { X } from "@lucide/vue"
import { ref } from "vue"

defineProps<{ open: boolean; loading: boolean; error: string }>()
const emit = defineEmits<{
  close: []
  submit: [title: string, content: string, sourceUri: string | null]
}>()

const title = ref("")
const content = ref("")
const sourceUri = ref("")

function submit(): void {
  if (!title.value.trim() || content.value.trim().length < 20) return
  emit("submit", title.value.trim(), content.value.trim(), sourceUri.value.trim() || null)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="dialog-backdrop" @click.self="emit('close')">
      <form class="dialog document-dialog" @submit.prevent="submit">
        <header>
          <div><p class="eyebrow">Knowledge base</p><h2>Add source document</h2></div>
          <button class="icon-button subtle" type="button" title="Close" @click="emit('close')"><X :size="18" /></button>
        </header>
        <label class="field-label">
          Title
          <input v-model="title" maxlength="500" placeholder="Internal market memo" required />
        </label>
        <label class="field-label">
          Source URL <span class="optional-label">Optional</span>
          <input v-model="sourceUri" type="url" maxlength="2048" placeholder="https://..." />
        </label>
        <label class="field-label">
          Document text
          <textarea
            v-model="content"
            rows="12"
            minlength="20"
            maxlength="1000000"
            placeholder="Paste the source text to index..."
            required
          />
          <small>{{ content.length.toLocaleString() }} characters</small>
        </label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <footer>
          <button class="text-button secondary" type="button" @click="emit('close')">Cancel</button>
          <button class="text-button primary" type="submit" :disabled="loading || content.trim().length < 20">
            {{ loading ? "Indexing..." : "Index document" }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>
