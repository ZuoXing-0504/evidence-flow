<script setup lang="ts">
import { CirclePlus, Search } from "@lucide/vue"
import { computed, ref } from "vue"

import StatusPill from "@/components/StatusPill.vue"
import { parseApiDate } from "@/dates"
import type { ResearchTask } from "@/types"

const props = defineProps<{
  tasks: ResearchTask[]
  selectedId: string | null
  loading: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  create: []
}>()

const filter = ref("")
const filteredTasks = computed(() => {
  const query = filter.value.trim().toLocaleLowerCase()
  if (!query) return props.tasks
  return props.tasks.filter((task) => task.topic.toLocaleLowerCase().includes(query))
})

function relativeDate(value: string): string {
  const timestamp = parseApiDate(value).getTime()
  const difference = Math.max(0, Date.now() - timestamp)
  if (difference < 60_000) return "刚刚"
  if (difference < 3_600_000) return `${Math.floor(difference / 60_000)} 分钟前`
  if (difference < 86_400_000) return `${Math.floor(difference / 3_600_000)} 小时前`
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(timestamp)
}
</script>

<template>
  <section class="task-panel" aria-label="研究任务">
    <div class="panel-heading task-panel-heading">
      <div>
        <p class="eyebrow">研究工作台</p>
        <h1>任务队列</h1>
      </div>
      <button class="icon-button primary" type="button" title="新建研究" @click="emit('create')">
        <CirclePlus :size="19" />
      </button>
    </div>

    <label class="search-field">
      <Search :size="16" />
      <input v-model="filter" type="search" placeholder="筛选研究任务" />
    </label>

    <div class="task-list" :aria-busy="loading">
      <button
        v-for="task in filteredTasks"
        :key="task.id"
        class="task-row"
        :class="{ selected: task.id === selectedId }"
        type="button"
        @click="emit('select', task.id)"
      >
        <span class="task-row-top">
          <StatusPill :status="task.status" />
          <time :datetime="task.created_at">{{ relativeDate(task.created_at) }}</time>
        </span>
        <strong>{{ task.topic }}</strong>
        <span class="task-row-meta">
          已反思 {{ task.iteration }} / {{ task.max_iterations }} 轮
        </span>
      </button>
      <p v-if="!loading && !filteredTasks.length" class="inline-empty">未找到研究任务</p>
      <div v-if="loading" class="task-loading" aria-label="正在加载研究任务">
        <span v-for="index in 4" :key="index" />
      </div>
    </div>
  </section>
</template>
