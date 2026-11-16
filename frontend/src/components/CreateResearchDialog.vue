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
            <p class="eyebrow">新建任务</p>
            <h2>发起深度研究</h2>
          </div>
          <button class="icon-button subtle" type="button" title="关闭" @click="emit('close')">
            <X :size="18" />
          </button>
        </header>
        <label class="field-label">
          研究主题
          <textarea
            v-model="topic"
            rows="5"
            minlength="3"
            maxlength="1000"
            placeholder="例如：多 Agent 系统在金融行业的落地现状与风险"
            autofocus
            required
          />
        </label>
        <label class="field-label">
          反思补搜轮次
          <span class="range-value">{{ maxIterations }}</span>
          <input v-model.number="maxIterations" type="range" min="0" max="5" step="1" />
        </label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <footer>
          <button class="text-button secondary" type="button" @click="emit('close')">取消</button>
          <button class="text-button primary" type="submit" :disabled="loading || topic.trim().length < 3">
            {{ loading ? "正在启动..." : "开始研究" }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>
