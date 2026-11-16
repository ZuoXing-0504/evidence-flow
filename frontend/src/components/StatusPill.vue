<script setup lang="ts">
import { computed } from "vue"

import type { ResearchStatus } from "@/types"

const props = defineProps<{ status: ResearchStatus | "indexing" | "indexed" }>()

const labels: Record<ResearchStatus | "indexing" | "indexed", string> = {
  queued: "排队中",
  running: "进行中",
  completed: "已完成",
  completed_with_warnings: "完成（有警告）",
  failed: "失败",
  cancelled: "已取消",
  indexing: "索引中",
  indexed: "已索引",
}

const label = computed(() => labels[props.status])
</script>

<template>
  <span class="status-pill" :class="`status-${status}`">
    <span class="status-dot" />{{ label }}
  </span>
</template>
