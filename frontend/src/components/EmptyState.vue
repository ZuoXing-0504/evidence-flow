<script setup lang="ts">
import type { Component } from "vue"

defineProps<{
  icon: Component
  title: string
  detail: string
}>()
</script>

<template>
  <div class="empty-state">
    <span class="empty-icon"><component :is="icon" :size="24" /></span>
    <h2>{{ title }}</h2>
    <p>{{ detail }}</p>
    <slot />
  </div>
</template>
