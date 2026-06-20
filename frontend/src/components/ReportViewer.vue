<template>
  <div class="report-viewer glass-panel">
    <div class="report-header no-print">
      <div class="header-title">
        <FileText class="doc-icon" />
        <h3>研究报告预览</h3>
      </div>
      <div v-if="content" class="actions">
        <button type="button" class="action-btn" @click="handleCopy" title="复制内容">
          <Copy class="btn-icon" />
          <span>复制</span>
        </button>
        <button type="button" class="action-btn" @click="handleExportMD" title="导出 Markdown">
          <Download class="btn-icon" />
          <span>MD</span>
        </button>
        <button type="button" class="action-btn" @click="handleExportHTML" title="导出 HTML">
          <FileCode class="btn-icon" />
          <span>HTML</span>
        </button>
        <button type="button" class="action-btn" @click="handlePrint" title="打印为 PDF">
          <Printer class="btn-icon" />
          <span>打印</span>
        </button>
      </div>
    </div>

    <!-- Print Only Header -->
    <div class="print-only print-header">
      <h1>{{ topic }}</h1>
      <p class="print-meta">由 Deep Research Agent 自动化生成 | 时间: {{ new Date().toLocaleString() }}</p>
    </div>

    <div ref="contentBody" class="report-body markdown-body" v-html="renderedHTML"></div>

    <div v-if="!content" class="empty-report no-print">
      <div class="loader-placeholder" v-if="isRunning">
        <div class="spinner"></div>
        <p>探索完成时，最终报告将在此逐步拼装渲染...</p>
      </div>
      <div v-else>
        <FileText class="empty-icon" />
        <p>暂无报告，请在左侧配置面板中发起新的探索课题。</p>
      </div>
    </div>

    <!-- Hover Reference Popover -->
    <div
      v-if="hoveredRef && hoveredRefContent"
      class="ref-popover glass-panel"
      :style="popoverStyle"
    >
      <div class="popover-title">{{ hoveredRefContent.title || '参考来源' }}</div>
      <div class="popover-url">{{ hoveredRefContent.url }}</div>
      <div v-if="hoveredRefContent.snippet" class="popover-snippet">{{ hoveredRefContent.snippet }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { FileText, Copy, Download, FileCode, Printer } from 'lucide-vue-next';
import { marked } from 'marked';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { exportToMarkdown, exportToHTML } from '../utils/exporter';

const props = defineProps<{
  content: string;
  sources: Array<{ url: string; title: string; snippet?: string }>;
  topic: string;
  isRunning: boolean;
}>();

const contentBody = ref<HTMLElement | null>(null);

// Hover reference states
const hoveredRef = ref<number | null>(null);
const hoveredRefContent = computed(() => {
  if (hoveredRef.value === null) return null;
  const idx = hoveredRef.value - 1;
  if (props.sources && props.sources[idx]) {
    return props.sources[idx];
  }
  return { url: '未知来源', title: `引用来源 [${hoveredRef.value}]` };
});

const popoverX = ref(0);
const popoverY = ref(0);
const popoverStyle = computed(() => ({
  top: `${popoverY.value}px`,
  left: `${popoverX.value}px`,
  position: 'fixed' as const
}));

// Marked parse rendering with KaTeX and custom citation nodes
const renderedHTML = computed(() => {
  if (!props.content) return '';

  // 1. Block formulas: $$ math $$
  let processed = props.content.replace(/\$\$\s*([\s\S]+?)\s*\$\$/g, (_, formula) => {
    try {
      return `<div class="math-block">${katex.renderToString(formula, { displayMode: true, throwOnError: false })}</div>`;
    } catch {
      return `<div class="math-block error">${formula}</div>`;
    }
  });

  // 2. Inline formulas: $ math $
  processed = processed.replace(/\$([^\$\n]+?)\$/g, (_, formula) => {
    try {
      return `<span class="math-inline">${katex.renderToString(formula, { displayMode: false, throwOnError: false })}</span>`;
    } catch {
      return `<span class="math-inline error">${formula}</span>`;
    }
  });

  // 3. Citations: [1] -> ref anchor
  processed = processed.replace(/\[(\d+)\](?!\()/g, (_, num) => {
    return `<a class="ref-anchor" data-ref="${num}">[${num}]</a>`;
  });

  // 4. Parse with marked
  return marked.parse(processed) as string;
});

// Setup hover listener for dynamically rendered references
const setupListeners = () => {
  if (!contentBody.value) return;
  const anchors = contentBody.value.querySelectorAll('.ref-anchor');
  anchors.forEach(a => {
    a.addEventListener('mouseenter', handleMouseEnter);
    a.addEventListener('mouseleave', handleMouseLeave);
  });
};

const handleMouseEnter = (e: Event) => {
  const target = e.currentTarget as HTMLElement;
  const refNum = parseInt(target.getAttribute('data-ref') || '0', 10);
  if (!refNum) return;

  const rect = target.getBoundingClientRect();
  popoverX.value = rect.left;
  popoverY.value = rect.bottom + 8; // 8px spacer
  hoveredRef.value = refNum;
};

const handleMouseLeave = () => {
  hoveredRef.value = null;
};

// Re-bind listeners on content render
watch(renderedHTML, () => {
  nextTick(() => {
    setupListeners();
  });
});

onMounted(() => {
  setupListeners();
});

onUnmounted(() => {
  if (!contentBody.value) return;
  const anchors = contentBody.value.querySelectorAll('.ref-anchor');
  anchors.forEach(a => {
    a.removeEventListener('mouseenter', handleMouseEnter);
    a.removeEventListener('mouseleave', handleMouseLeave);
  });
});

// Action triggers
const handleCopy = () => {
  navigator.clipboard.writeText(props.content);
  alert('报告已成功复制到剪贴板！');
};

const handleExportMD = () => {
  const filename = (props.topic || 'research_report').replace(/\s+/g, '_');
  exportToMarkdown(filename, props.content);
};

const handleExportHTML = () => {
  const filename = (props.topic || 'research_report').replace(/\s+/g, '_');
  exportToHTML(filename, props.topic || '深度研究报告', renderedHTML.value);
};

const handlePrint = () => {
  window.print();
};
</script>

<style scoped>
.report-viewer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
  overflow: hidden;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--glass-border);
  padding-bottom: 16px;
  margin-bottom: 20px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.doc-icon {
  color: var(--color-primary);
  width: 22px;
  height: 22px;
}

.header-title h3 {
  font-size: 1.1rem;
  color: var(--text-main);
  margin: 0;
}

.actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--glass-border);
  color: var(--text-muted);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: 0.8rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-main);
  border-color: var(--color-primary);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.report-body {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  line-height: 1.7;
}

.markdown-body {
  font-size: 0.95rem;
  color: #e2e8f0;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  color: var(--text-main);
  margin-top: 1.6em;
  margin-bottom: 0.6em;
  font-weight: 600;
}

.markdown-body :deep(h1) {
  font-size: 1.75rem;
  border-bottom: 1px solid var(--glass-border);
  padding-bottom: 8px;
}

.markdown-body :deep(h2) {
  font-size: 1.4rem;
}

.markdown-body :deep(h3) {
  font-size: 1.15rem;
}

.markdown-body :deep(p) {
  margin-bottom: 1.2em;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-bottom: 1.2em;
  padding-left: 20px;
}

.markdown-body :deep(li) {
  margin-bottom: 0.4em;
}

.markdown-body :deep(code) {
  background: rgba(15, 23, 42, 0.6);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  font-size: 0.85em;
  border: 1px solid var(--glass-border);
}

.markdown-body :deep(pre) {
  background: rgba(15, 23, 42, 0.8);
  padding: 16px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  border: 1px solid var(--glass-border);
  margin-bottom: 1.2em;
}

.markdown-body :deep(pre code) {
  background: transparent;
  border: none;
  padding: 0;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--color-primary);
  padding-left: 16px;
  color: var(--text-muted);
  margin: 20px 0;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  padding-top: 8px;
  padding-bottom: 8px;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1.2em;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--glass-border);
  padding: 10px 14px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: rgba(255, 255, 255, 0.05);
  font-weight: 600;
}

.markdown-body :deep(.ref-anchor) {
  color: var(--color-primary);
  font-size: 0.85em;
  font-weight: 600;
  cursor: pointer;
  margin-left: 2px;
  margin-right: 2px;
}

.markdown-body :deep(.ref-anchor:hover) {
  color: var(--color-secondary);
  text-decoration: underline;
}

.markdown-body :deep(.math-block) {
  display: flex;
  justify-content: center;
  margin: 1.5em 0;
  overflow-x: auto;
  padding: 8px 0;
}

.markdown-body :deep(.math-inline) {
  padding: 0 2px;
}

.empty-report {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-dark);
  font-size: 0.95rem;
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: var(--text-dark);
  margin-bottom: 16px;
  opacity: 0.5;
}

.loader-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(56, 189, 248, 0.1);
  border-top: 3px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.ref-popover {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid var(--color-primary);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  border-radius: var(--radius-md);
  padding: 14px;
  max-width: 320px;
  z-index: 1000;
  pointer-events: none;
  animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.popover-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
  word-break: break-all;
}

.popover-url {
  font-size: 0.7rem;
  color: var(--color-primary);
  margin-bottom: 8px;
  word-break: break-all;
}

.popover-snippet {
  font-size: 0.75rem;
  color: var(--text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.print-only {
  display: none;
}

@media print {
  .no-print {
    display: none !important;
  }
  
  .print-only {
    display: block !important;
  }

  .print-header {
    border-bottom: 2px solid #0f172a;
    padding-bottom: 12px;
    margin-bottom: 30px;
  }

  .print-header h1 {
    font-size: 2.2rem;
    color: #0f172a;
  }

  .print-meta {
    font-size: 0.8rem;
    color: #475569;
    margin-top: 6px;
  }

  .report-viewer {
    padding: 0;
    overflow: visible;
  }

  .report-body {
    overflow: visible;
  }

  .markdown-body {
    color: #0f172a !important;
  }

  .markdown-body :deep(h1),
  .markdown-body :deep(h2),
  .markdown-body :deep(h3) {
    color: #0f172a !important;
    page-break-after: avoid;
  }

  .markdown-body :deep(pre),
  .markdown-body :deep(blockquote) {
    border-color: #cbd5e1 !important;
    background: #f8fafc !important;
    page-break-inside: avoid;
  }

  .markdown-body :deep(td),
  .markdown-body :deep(th) {
    border-color: #cbd5e1 !important;
  }
}
</style>
