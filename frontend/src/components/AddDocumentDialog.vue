<script setup lang="ts">
import { FileText, Upload, X } from "@lucide/vue"
import { computed, ref, watch } from "vue"

import {
  DOCUMENT_FILE_ACCEPT,
  documentFileError,
  formatFileSize,
} from "@/documents"

const props = defineProps<{ open: boolean; loading: boolean; error: string }>()
const emit = defineEmits<{
  close: []
  submit: [title: string, content: string, sourceUri: string | null]
  upload: [file: File, title: string | null]
}>()

const mode = ref<"upload" | "paste">("upload")
const title = ref("")
const content = ref("")
const sourceUri = ref("")
const selectedFile = ref<File | null>(null)
const fileError = ref("")
const fileInput = ref<HTMLInputElement | null>(null)

const canSubmit = computed(() =>
  mode.value === "upload"
    ? Boolean(selectedFile.value && !fileError.value)
    : Boolean(title.value.trim() && content.value.trim().length >= 20),
)

function chooseFile(): void {
  fileInput.value?.click()
}

function selectFile(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  selectedFile.value = file
  fileError.value = file ? documentFileError(file) : ""
}

function submit(): void {
  if (!canSubmit.value) return
  if (mode.value === "upload" && selectedFile.value) {
    emit("upload", selectedFile.value, title.value.trim() || null)
    return
  }
  emit("submit", title.value.trim(), content.value.trim(), sourceUri.value.trim() || null)
}

function reset(): void {
  mode.value = "upload"
  title.value = ""
  content.value = ""
  sourceUri.value = ""
  selectedFile.value = null
  fileError.value = ""
  if (fileInput.value) fileInput.value.value = ""
}

watch(
  () => props.open,
  (open) => {
    if (!open) reset()
  },
)
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="dialog-backdrop" @click.self="emit('close')">
      <form class="dialog document-dialog" @submit.prevent="submit">
        <header>
          <div><p class="eyebrow">知识库</p><h2>添加来源文档</h2></div>
          <button class="icon-button subtle" type="button" title="关闭" @click="emit('close')"><X :size="18" /></button>
        </header>

        <div class="document-mode-tabs" role="tablist" aria-label="文档添加方式">
          <button type="button" role="tab" :aria-selected="mode === 'upload'" :class="{ active: mode === 'upload' }" @click="mode = 'upload'">
            <Upload :size="15" /> 上传文件
          </button>
          <button type="button" role="tab" :aria-selected="mode === 'paste'" :class="{ active: mode === 'paste' }" @click="mode = 'paste'">
            <FileText :size="15" /> 粘贴正文
          </button>
        </div>

        <template v-if="mode === 'upload'">
          <input
            ref="fileInput"
            class="visually-hidden"
            type="file"
            :accept="DOCUMENT_FILE_ACCEPT"
            @change="selectFile"
          />
          <button class="file-dropzone" type="button" @click="chooseFile">
            <span class="file-dropzone-icon"><Upload :size="22" /></span>
            <strong>{{ selectedFile ? selectedFile.name : "选择本地文档" }}</strong>
            <span>{{ selectedFile ? formatFileSize(selectedFile.size) : "支持 TXT、Markdown、PDF，最大 10 MB" }}</span>
          </button>
          <label class="field-label">
            文档标题 <span class="optional-label">选填，默认使用文件名</span>
            <input v-model="title" maxlength="500" placeholder="例如：2026 金融科技行业报告" />
          </label>
          <p v-if="fileError" class="form-error">{{ fileError }}</p>
        </template>

        <template v-else>
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
              rows="10"
              minlength="20"
              maxlength="1000000"
              placeholder="粘贴需要建立索引的来源文本..."
              required
            />
            <small>{{ content.length.toLocaleString("zh-CN") }} 个字符</small>
          </label>
        </template>

        <p v-if="error" class="form-error">{{ error }}</p>
        <footer>
          <button class="text-button secondary" type="button" @click="emit('close')">取消</button>
          <button class="text-button primary" type="submit" :disabled="loading || !canSubmit">
            {{ loading ? "正在索引..." : "建立索引" }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>
