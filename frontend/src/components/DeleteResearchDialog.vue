<script setup lang="ts">
import { Trash2, X } from "@lucide/vue"

defineProps<{ open: boolean; topic: string; loading: boolean; error: string }>()
const emit = defineEmits<{ close: []; confirm: [] }>()
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="dialog-backdrop" @click.self="emit('close')">
      <section class="dialog confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
        <header>
          <div>
            <p class="eyebrow danger-copy">删除任务</p>
            <h2 id="delete-title">确认删除研究记录？</h2>
          </div>
          <button class="icon-button subtle" type="button" title="关闭" @click="emit('close')">
            <X :size="18" />
          </button>
        </header>
        <p class="confirm-copy">“{{ topic }}”的报告、证据和执行记录将被永久删除，此操作无法撤销。</p>
        <p v-if="error" class="form-error">{{ error }}</p>
        <footer>
          <button class="text-button secondary" type="button" :disabled="loading" @click="emit('close')">取消</button>
          <button class="text-button danger solid" type="button" :disabled="loading" @click="emit('confirm')">
            <Trash2 :size="16" /> {{ loading ? "正在删除..." : "确认删除" }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>
