<script setup lang="ts">
import { computed } from "vue"

import type { ResearchStatus } from "@/types"

const props = defineProps<{ status: ResearchStatus | "indexing" | "indexed" }>()

const label = computed(() =>
  props.status
    .split("_")
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" "),
)
</script>

<template>
  <span class="status-pill" :class="`status-${status}`">
    <span class="status-dot" />{{ label }}
  </span>
</template>
