<script setup lang="ts">
import { AlertTriangle, CheckCircle2, Scale } from "@lucide/vue"
import { computed } from "vue"

import { confidenceLabel, evidenceLabel, summarizeFindings } from "@/findings"
import type { Evidence, Finding } from "@/types"

const props = defineProps<{ findings: Finding[]; evidence: Evidence[] }>()
const summary = computed(() => summarizeFindings(props.findings))

function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}
</script>

<template>
  <div class="findings-view">
    <header class="findings-heading">
      <div>
        <p class="eyebrow">Analyst 输出</p>
        <h2>证据分析</h2>
      </div>
      <div class="finding-summary">
        <span><CheckCircle2 :size="15" />平均置信度 <strong>{{ percent(summary.averageConfidence) }}</strong></span>
        <span :class="{ warning: summary.conflictCount }"><Scale :size="15" />冲突结论 <strong>{{ summary.conflictCount }}</strong></span>
      </div>
    </header>

    <div v-if="findings.length" class="finding-list">
      <article v-for="(finding, index) in findings" :key="finding.id" class="finding-item">
        <header>
          <span class="finding-index">{{ String(index + 1).padStart(2, "0") }}</span>
          <span class="confidence-label">{{ confidenceLabel(finding.confidence) }}</span>
        </header>
        <div class="confidence-track" :aria-label="`置信度 ${percent(finding.confidence)}`">
          <span :style="{ width: percent(finding.confidence) }" />
        </div>
        <p class="finding-claim">{{ finding.claim }}</p>
        <div class="evidence-links support-links">
          <strong>支持证据</strong>
          <span v-for="id in finding.supporting_evidence_ids" :key="id">{{ evidenceLabel(evidence, id) }}</span>
        </div>
        <div v-if="finding.opposing_evidence_ids.length" class="evidence-links opposing-links">
          <strong><AlertTriangle :size="13" />反对证据</strong>
          <span v-for="id in finding.opposing_evidence_ids" :key="id">{{ evidenceLabel(evidence, id) }}</span>
        </div>
      </article>
    </div>
    <p v-else class="inline-empty">当前任务没有生成可展示的分析结论</p>
  </div>
</template>
