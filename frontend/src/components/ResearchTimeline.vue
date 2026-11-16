<script setup lang="ts">
import { Check, Circle, LoaderCircle, X } from "@lucide/vue"
import { computed } from "vue"

import type { ResearchEvent, ResearchNode } from "@/types"

const props = defineProps<{ events: ResearchEvent[]; taskTerminal: boolean }>()

const stages: { node: ResearchNode; label: string }[] = [
  { node: "memory_recall", label: "记忆召回" },
  { node: "intent_router", label: "意图路由" },
  { node: "planner", label: "研究规划" },
  { node: "web_scout", label: "联网检索" },
  { node: "local_scout", label: "本地知识检索" },
  { node: "evidence_judge", label: "证据评审" },
  { node: "analyst", label: "综合分析" },
  { node: "reflect", label: "缺口反思" },
  { node: "writer", label: "报告撰写" },
  { node: "citation_validator", label: "引用校验" },
  { node: "memory_commit", label: "记忆沉淀" },
]

const nodeState = computed(() => {
  const state = new Map<ResearchNode, "waiting" | "running" | "done" | "failed">()
  for (const stage of stages) state.set(stage.node, "waiting")
  for (const event of props.events) {
    if (!event.node) continue
    if (event.type === "node_started") state.set(event.node, "running")
    if (event.type === "node_completed") state.set(event.node, "done")
    if (event.type === "node_failed") state.set(event.node, "failed")
  }
  return state
})
</script>

<template>
  <div class="timeline" :class="{ terminal: taskTerminal }">
    <div v-for="stage in stages" :key="stage.node" class="timeline-step" :class="nodeState.get(stage.node)">
      <span class="timeline-marker">
        <Check v-if="nodeState.get(stage.node) === 'done'" :size="13" />
        <LoaderCircle v-else-if="nodeState.get(stage.node) === 'running'" :size="13" />
        <X v-else-if="nodeState.get(stage.node) === 'failed'" :size="13" />
        <Circle v-else :size="10" />
      </span>
      <span>{{ stage.label }}</span>
    </div>
  </div>
</template>
