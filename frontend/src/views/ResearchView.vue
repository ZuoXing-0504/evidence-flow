<script setup lang="ts">
import { AlertTriangle, BookOpenText, FileSearch, OctagonX, RefreshCw, Trash2 } from "@lucide/vue"
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue"

import { ApiError, researchApi, streamResearchEvents } from "@/api"
import AppShell from "@/components/AppShell.vue"
import CreateResearchDialog from "@/components/CreateResearchDialog.vue"
import DeleteResearchDialog from "@/components/DeleteResearchDialog.vue"
import EmptyState from "@/components/EmptyState.vue"
import EvidencePanel from "@/components/EvidencePanel.vue"
import FindingsView from "@/components/FindingsView.vue"
import ReportView from "@/components/ReportView.vue"
import ResearchTimeline from "@/components/ResearchTimeline.vue"
import ResearchMetricsPanel from "@/components/ResearchMetricsPanel.vue"
import StatusPill from "@/components/StatusPill.vue"
import TaskList from "@/components/TaskList.vue"
import { formatApiDate } from "@/dates"
import { isTerminalResearchStatus } from "@/status"
import type { Evidence, Finding, Report, ResearchEvent, ResearchMetrics, ResearchTask } from "@/types"

const tasks = ref<ResearchTask[]>([])
const selected = ref<ResearchTask | null>(null)
const report = ref<Report | null>(null)
const evidence = ref<Evidence[]>([])
const findings = ref<Finding[]>([])
const metrics = ref<ResearchMetrics | null>(null)
const events = ref<ResearchEvent[]>([])
const loadingTasks = ref(true)
const loadingDetail = ref(false)
const creating = ref(false)
const cancelling = ref(false)
const deleting = ref(false)
const deleteDialogOpen = ref(false)
const deleteError = ref("")
const dialogOpen = ref(false)
const error = ref("")
const createError = ref("")
const mobileTab = ref<"progress" | "report" | "findings" | "evidence">("progress")
const resultMode = ref<"report" | "findings">("report")
let streamController: AbortController | null = null

const terminal = computed(() =>
  selected.value
    ? ["completed", "completed_with_warnings", "failed", "cancelled"].includes(selected.value.status)
    : false,
)

const canCancel = computed(() =>
  selected.value ? ["queued", "running"].includes(selected.value.status) : false,
)

const canDelete = computed(() =>
  selected.value ? isTerminalResearchStatus(selected.value.status) : false,
)

function errorMessage(value: unknown): string {
  return value instanceof ApiError ? value.message : "无法连接研究服务，请稍后重试"
}

async function loadTasks(selectFirst = true): Promise<void> {
  loadingTasks.value = true
  error.value = ""
  try {
    tasks.value = (await researchApi.list()).items
    if (selectFirst && !selected.value && tasks.value[0]) await selectTask(tasks.value[0].id)
  } catch (value) {
    error.value = errorMessage(value)
  } finally {
    loadingTasks.value = false
  }
}

async function loadCompletedAssets(task: ResearchTask): Promise<void> {
  if (!["completed", "completed_with_warnings"].includes(task.status)) return
  const [nextReport, nextEvidence, nextFindings] = await Promise.all([
    researchApi.report(task.id),
    researchApi.evidence(task.id),
    researchApi.findings(task.id),
  ])
  report.value = nextReport
  evidence.value = nextEvidence
  findings.value = nextFindings
  resultMode.value = "report"
  mobileTab.value = "report"
}

async function refreshSelected(): Promise<void> {
  if (!selected.value) return
  const [task, nextMetrics] = await Promise.all([
    researchApi.get(selected.value.id),
    researchApi.metrics(selected.value.id),
  ])
  selected.value = task
  metrics.value = nextMetrics
  const index = tasks.value.findIndex((item) => item.id === task.id)
  if (index >= 0) tasks.value[index] = task
  await loadCompletedAssets(task)
}

async function beginStream(task: ResearchTask): Promise<void> {
  streamController?.abort()
  streamController = new AbortController()
  try {
    await streamResearchEvents(
      task.id,
      (event) => {
        if (events.value.some((item) => item.id === event.id)) return
        events.value.push(event)
      },
      streamController.signal,
    )
    await refreshSelected()
  } catch (value) {
    if (!(value instanceof DOMException && value.name === "AbortError")) {
      error.value = errorMessage(value)
    }
  }
}

async function selectTask(id: string): Promise<void> {
  if (selected.value?.id === id && !loadingDetail.value) return
  streamController?.abort()
  loadingDetail.value = true
  error.value = ""
  report.value = null
  evidence.value = []
  findings.value = []
  metrics.value = null
  events.value = []
  resultMode.value = "report"
  mobileTab.value = "progress"
  try {
    const [task, nextMetrics] = await Promise.all([researchApi.get(id), researchApi.metrics(id)])
    selected.value = task
    metrics.value = nextMetrics
    await nextTick()
    void beginStream(selected.value)
  } catch (value) {
    error.value = errorMessage(value)
  } finally {
    loadingDetail.value = false
  }
}

async function createResearch(topic: string, maxIterations: number): Promise<void> {
  creating.value = true
  createError.value = ""
  try {
    const task = await researchApi.create(topic, maxIterations)
    tasks.value.unshift(task)
    dialogOpen.value = false
    selected.value = null
    await selectTask(task.id)
  } catch (value) {
    createError.value = errorMessage(value)
  } finally {
    creating.value = false
  }
}

async function cancelTask(): Promise<void> {
  if (!selected.value || !canCancel.value) return
  cancelling.value = true
  try {
    selected.value = await researchApi.cancel(selected.value.id)
    await refreshSelected()
  } catch (value) {
    error.value = errorMessage(value)
  } finally {
    cancelling.value = false
  }
}

async function deleteTask(): Promise<void> {
  if (!selected.value || !canDelete.value) return
  deleting.value = true
  deleteError.value = ""
  const taskId = selected.value.id
  try {
    await researchApi.remove(taskId)
    streamController?.abort()
    tasks.value = tasks.value.filter((task) => task.id !== taskId)
    selected.value = null
    report.value = null
    evidence.value = []
    findings.value = []
    metrics.value = null
    events.value = []
    deleteDialogOpen.value = false
    if (tasks.value[0]) await selectTask(tasks.value[0].id)
  } catch (value) {
    deleteError.value = errorMessage(value)
  } finally {
    deleting.value = false
  }
}

onMounted(() => void loadTasks())
onBeforeUnmount(() => streamController?.abort())
</script>

<template>
  <AppShell>
    <div class="research-workspace">
      <TaskList
        :tasks="tasks"
        :selected-id="selected?.id ?? null"
        :loading="loadingTasks"
        @select="selectTask"
        @create="dialogOpen = true"
      />

      <section class="research-main">
        <div v-if="error" class="error-banner">
          <AlertTriangle :size="17" />
          <span>{{ error }}</span>
          <button class="icon-button subtle" type="button" title="重试" @click="loadTasks(false)">
            <RefreshCw :size="16" />
          </button>
        </div>

        <EmptyState
          v-if="!selected && !loadingTasks"
          :icon="FileSearch"
          title="尚未选择研究任务"
          detail="发起一个研究任务，生成有证据支撑的深度报告。"
        >
          <button class="text-button primary" type="button" @click="dialogOpen = true">
            新建研究
          </button>
        </EmptyState>

        <template v-else-if="selected">
          <header class="research-header">
            <div class="research-title-block">
              <div class="research-title-meta">
                <StatusPill :status="selected.status" />
                <span>{{ formatApiDate(selected.created_at) }}</span>
              </div>
              <h1>{{ selected.topic }}</h1>
              <p v-if="selected.warnings.length" class="warning-copy">
                {{ selected.warnings.join(" · ") }}
              </p>
            </div>
            <div class="research-header-actions">
              <button
                v-if="canCancel"
                class="text-button danger"
                type="button"
                :disabled="cancelling"
                @click="cancelTask"
              >
                <OctagonX :size="16" /> {{ cancelling ? "正在取消" : "取消任务" }}
              </button>
              <button
                v-if="canDelete"
                class="icon-button danger-icon"
                type="button"
                title="删除研究任务"
                @click="deleteDialogOpen = true"
              >
                <Trash2 :size="17" />
              </button>
            </div>
          </header>

          <div class="mobile-segments">
            <button :class="{ active: mobileTab === 'progress' }" @click="mobileTab = 'progress'">进度</button>
            <button :class="{ active: mobileTab === 'report' }" @click="mobileTab = 'report'; resultMode = 'report'">报告</button>
            <button :class="{ active: mobileTab === 'findings' }" @click="mobileTab = 'findings'; resultMode = 'findings'">分析</button>
            <button :class="{ active: mobileTab === 'evidence' }" @click="mobileTab = 'evidence'">证据</button>
          </div>

          <div class="research-body" :class="`mobile-${mobileTab}`">
            <section class="progress-column">
              <div class="section-heading">
                <div>
                  <p class="eyebrow">执行流程</p>
                  <h2>Agent 进度</h2>
                </div>
                <span class="iteration-label">第 {{ selected.iteration }} / {{ selected.max_iterations }} 轮</span>
              </div>
              <ResearchTimeline :events="events" :task-terminal="terminal" />
              <ResearchMetricsPanel :metrics="metrics" />
            </section>

            <section class="report-column">
              <div v-if="report" class="result-segments" aria-label="研究结果视图">
                <button :class="{ active: resultMode === 'report' }" type="button" @click="resultMode = 'report'">研究报告</button>
                <button :class="{ active: resultMode === 'findings' }" type="button" @click="resultMode = 'findings'">分析结论</button>
              </div>
              <ReportView
                v-if="report && resultMode === 'report'"
                :topic="selected.topic"
                :content="report.content"
                :citation-errors="report.citation_errors"
              />
              <FindingsView
                v-else-if="report && resultMode === 'findings'"
                :findings="findings"
                :evidence="evidence"
              />
              <EmptyState
                v-else
                :icon="BookOpenText"
                title="报告生成中"
                :detail="terminal ? '任务已结束，但未生成报告。' : '证据评审完成后，Writer Agent 将生成研究报告。'"
              />
            </section>
          </div>
        </template>
      </section>

      <EvidencePanel
        v-if="selected"
        :evidence="evidence"
        :loading="loadingDetail || (!terminal && !evidence.length)"
        :class="{ 'mobile-evidence-active': mobileTab === 'evidence' }"
      />
    </div>

    <CreateResearchDialog
      :open="dialogOpen"
      :loading="creating"
      :error="createError"
      @close="dialogOpen = false"
      @submit="createResearch"
    />
    <DeleteResearchDialog
      :open="deleteDialogOpen"
      :topic="selected?.topic ?? ''"
      :loading="deleting"
      :error="deleteError"
      @close="deleteDialogOpen = false"
      @confirm="deleteTask"
    />
  </AppShell>
</template>
