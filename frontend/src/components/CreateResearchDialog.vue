<script setup lang="ts">
import { X } from "@lucide/vue"
import { ref } from "vue"

defineProps<{ open: boolean; loading: boolean; error: string }>()
const emit = defineEmits<{
  close: []
  submit: [topic: string, maxIterations: number]
}>()

const topic = ref("")
const maxIterations = ref(2)

function submit(): void {
  const normalized = topic.value.trim()
  if (normalized.length < 3) return
  emit("submit", normalized, maxIterations.value)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="dialog-backdrop" @click.self="emit('close')">
      <form class="dialog" @submit.prevent="submit">
        <header>
          <div>
            <p class="eyebrow">New task</p>
            <h2>Start deep research</h2>
          </div>
          <button class="icon-button subtle" type="button" title="Close" @click="emit('close')">
            <X :size="18" />
          </button>
        </header>
        <label class="field-label">
          Research topic
          <textarea
            v-model="topic"
            rows="5"
            minlength="3"
            maxlength="1000"
            placeholder="e.g. Enterprise AI agent adoption in regulated industries"
            autofocus
            required
          />
        </label>
        <label class="field-label">
          Reflection rounds
          <span class="range-value">{{ maxIterations }}</span>
          <input v-model.number="maxIterations" type="range" min="0" max="5" step="1" />
        </label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <footer>
          <button class="text-button secondary" type="button" @click="emit('close')">Cancel</button>
          <button class="text-button primary" type="submit" :disabled="loading || topic.trim().length < 3">
            {{ loading ? "Starting..." : "Start research" }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>
