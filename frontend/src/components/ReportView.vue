<script setup lang="ts">
import { Download, Printer, ShieldAlert, ShieldCheck } from "@lucide/vue"
import { computed } from "vue"

import { downloadMarkdownReport, formatCitationError, renderReportMarkdown } from "@/report"

const props = defineProps<{ topic: string; content: string; citationErrors: string[] }>()

const rendered = computed(() => renderReportMarkdown(props.content))

function download(): void {
  downloadMarkdownReport(props.topic, props.content)
}

function printReport(): void {
  window.print()
}
</script>

<template>
  <div class="report-view">
    <div class="report-toolbar">
      <span v-if="!citationErrors.length" class="citation-audit valid">
        <ShieldCheck :size="16" /> 引用校验通过
      </span>
      <span v-else class="citation-audit invalid">
        <ShieldAlert :size="16" /> 发现 {{ citationErrors.length }} 个引用问题
      </span>
      <div class="report-actions">
        <button class="icon-button" type="button" title="下载 Markdown 报告" @click="download">
          <Download :size="17" />
        </button>
        <button class="icon-button" type="button" title="打印或另存为 PDF" @click="printReport">
          <Printer :size="17" />
        </button>
      </div>
    </div>
    <ul v-if="citationErrors.length" class="citation-errors">
      <li v-for="item in citationErrors" :key="item">{{ formatCitationError(item) }}</li>
    </ul>
    <article class="report-content" v-html="rendered" />
  </div>
</template>
