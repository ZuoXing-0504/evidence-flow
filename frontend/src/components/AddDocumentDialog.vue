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
          <div><p class="eyebrow">知识库</p><h2>添加来源文档</h2></div>
          <button class="icon-button subtle" type="button" title="关闭" @click="emit('close')"><X :size="18" /></button>
        </header>
        <label class="field-label">
          标题
          <input v-model="title" maxlength="500" placeholder="例如：行业调研内部备忘录" required />
        </label>
        <label class="field-label">
          来源链接 <span class="optional-label">选填</span>
          <input v-model="sourceUri" type="url" maxlength="2048" placeholder="https://..." />
        </label>
        <label class="field-label">
          文档正文
          <textarea
            v-model="content"
            rows="12"
            minlength="20"
            maxlength="1000000"
            placeholder="粘贴需要建立索引的来源文本..."
            required
          />
          <small>{{ content.length.toLocaleString("zh-CN") }} 个字符</small>
        </label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <footer>
          <button class="text-button secondary" type="button" @click="emit('close')">取消</button>
          <button class="text-button primary" type="submit" :disabled="loading || content.trim().length < 20">
            {{ loading ? "正在索引..." : "建立索引" }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>
