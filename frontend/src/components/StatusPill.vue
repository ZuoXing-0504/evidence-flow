<script setup lang="ts">
import { computed } from "vue"

import { statusLabel, type DisplayStatus } from "@/status"

const props = defineProps<{ status: DisplayStatus }>()

const label = computed(() => statusLabel(props.status))
</script>

<template>
  <span class="status-pill" :class="`status-${status}`">
    <span class="status-dot" />{{ label }}
  </span>
</template>
