<script setup lang="ts">
import { Check, Circle, LoaderCircle, X } from "@lucide/vue"
import { computed } from "vue"

import type { ResearchEvent, ResearchNode } from "@/types"

const props = defineProps<{ events: ResearchEvent[]; taskTerminal: boolean }>()

const stages: { node: ResearchNode; label: string }[] = [
  { node: "memory_recall", label: "Memory recall" },
  { node: "intent_router", label: "Intent routing" },
  { node: "planner", label: "Research plan" },
  { node: "web_scout", label: "Web search" },
  { node: "local_scout", label: "Local knowledge" },
  { node: "evidence_judge", label: "Evidence review" },
  { node: "analyst", label: "Analysis" },
  { node: "reflect", label: "Gap reflection" },
  { node: "writer", label: "Report writing" },
  { node: "citation_validator", label: "Citation check" },
  { node: "memory_commit", label: "Memory commit" },
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
