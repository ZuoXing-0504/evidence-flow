<script setup lang="ts">
import MarkdownIt from "markdown-it"
import { computed } from "vue"

const props = defineProps<{ content: string }>()

const markdown = new MarkdownIt({ html: false, linkify: true, typographer: true })
const rendered = computed(() => markdown.render(props.content))
</script>

<template>
  <article class="report-content" v-html="rendered" />
</template>
