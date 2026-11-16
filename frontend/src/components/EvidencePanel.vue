<script setup lang="ts">
import { ExternalLink, FileText, Globe2, History } from "@lucide/vue"
import { computed, ref } from "vue"

import type { Evidence } from "@/types"

const props = defineProps<{ evidence: Evidence[]; loading: boolean }>()
const active = ref<"all" | "web" | "local" | "memory">("all")

const filtered = computed(() =>
  active.value === "all"
    ? props.evidence
    : props.evidence.filter((item) => item.source_type === active.value),
)

const sourceIcon = {
  web: Globe2,
  local: FileText,
  memory: History,
}

function percent(value: number | null): string {
  return value === null ? "--" : `${Math.round(value * 100)}%`
}
</script>

<template>
  <section class="evidence-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">Sources</p>
        <h2>Evidence</h2>
      </div>
      <span class="count-badge">{{ evidence.length }}</span>
    </div>

    <div class="segmented-control" aria-label="Filter evidence">
      <button
        v-for="option in ['all', 'web', 'local', 'memory'] as const"
        :key="option"
        type="button"
        :class="{ active: active === option }"
        @click="active = option"
      >
        {{ option }}
      </button>
    </div>

    <div class="evidence-list" :aria-busy="loading">
      <article v-for="item in filtered" :key="item.domain_id" class="evidence-item">
        <header>
          <span class="source-icon"><component :is="sourceIcon[item.source_type]" :size="15" /></span>
          <span class="citation-label">{{ item.citation_id ?? "Uncited" }}</span>
          <a v-if="item.url" :href="item.url" target="_blank" rel="noopener noreferrer" title="Open source">
            <ExternalLink :size="15" />
          </a>
        </header>
        <h3>{{ item.title }}</h3>
        <p>{{ item.content }}</p>
        <dl>
          <div><dt>Relevance</dt><dd>{{ percent(item.relevance_score) }}</dd></div>
          <div><dt>Credibility</dt><dd>{{ percent(item.credibility_score) }}</dd></div>
        </dl>
      </article>
      <p v-if="!loading && !filtered.length" class="inline-empty">No evidence in this view.</p>
      <div v-if="loading" class="evidence-loading"><span v-for="index in 3" :key="index" /></div>
    </div>
  </section>
</template>
