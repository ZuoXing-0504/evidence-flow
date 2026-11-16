<script setup lang="ts">
import { Activity, Clock3, FileCheck2, GitBranch, Quote, TimerReset } from "@lucide/vue"
import { computed } from "vue"

import { formatDuration, nodeLabel } from "@/metrics"
import type { ResearchMetrics } from "@/types"

const props = defineProps<{ metrics: ResearchMetrics | null }>()
const maximumDuration = computed(() =>
  Math.max(1, ...(props.metrics?.node_metrics.map((item) => item.duration_ms) ?? [])),
)
</script>

<template>
  <section class="metrics-panel" aria-label="运行指标">
    <div class="metrics-heading">
      <p class="eyebrow">可观测性</p>
      <h3>运行指标</h3>
    </div>
    <div v-if="metrics" class="metrics-grid">
      <div>
        <Clock3 :size="14" />
        <span>总耗时</span>
        <strong>{{ formatDuration(metrics.total_duration_ms) }}</strong>
      </div>
      <div>
        <TimerReset :size="14" />
        <span>排队耗时</span>
        <strong>{{ formatDuration(metrics.queue_duration_ms) }}</strong>
      </div>
      <div>
        <Activity :size="14" />
        <span>Agent 调用</span>
        <strong>{{ metrics.agent_run_count }}</strong>
      </div>
      <div>
        <FileCheck2 :size="14" />
        <span>有效证据</span>
        <strong>{{ metrics.evidence_count }}</strong>
      </div>
      <div>
        <GitBranch :size="14" />
        <span>分析结论</span>
        <strong>{{ metrics.finding_count }}</strong>
      </div>
      <div>
        <Quote :size="14" />
        <span>有效引用</span>
        <strong>{{ metrics.citation_count }}</strong>
      </div>
    </div>
    <div v-if="metrics?.node_metrics.length" class="node-metrics">
      <div class="node-metrics-title">
        <span>节点耗时</span>
        <span>执行次数</span>
      </div>
      <div v-for="item in metrics.node_metrics" :key="item.node" class="node-metric-row">
        <div>
          <span>{{ nodeLabel(item.node) }}</span>
          <strong>{{ formatDuration(item.duration_ms) }}</strong>
        </div>
        <span class="node-run-count">{{ item.run_count }}</span>
        <span class="node-duration-track">
          <span :style="{ width: `${Math.max(4, item.duration_ms / maximumDuration * 100)}%` }" />
        </span>
      </div>
    </div>
    <p v-else-if="!metrics" class="metrics-empty">任务启动后将生成运行指标</p>
  </section>
</template>
