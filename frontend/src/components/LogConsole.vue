<template>
  <div class="log-console glass-panel">
    <div class="console-header">
      <div class="header-title">
        <Terminal class="terminal-icon" />
        <h3>执行追踪终端</h3>
      </div>
      <div class="filters">
        <button
          type="button"
          v-for="lvl in levels"
          :key="lvl.value"
          :class="['filter-btn', { active: currentLevel === lvl.value }]"
          @click="currentLevel = lvl.value"
        >
          {{ lvl.label }}
        </button>
      </div>
    </div>

    <div ref="logContainer" class="console-body" @scroll="handleScroll">
      <div v-if="filteredLogs.length === 0" class="empty-logs">
        <span class="pulse-text">等待探索任务启动，实时日志流将在此输出...</span>
      </div>
      <div v-else class="log-lines">
        <div
          v-for="(log, idx) in filteredLogs"
          :key="idx"
          :class="['log-line', getLogClass(log)]"
        >
          <span class="log-time">{{ getLogTime(log) }}</span>
          <span class="log-message" v-html="formatLogMessage(log)"></span>
        </div>
      </div>
    </div>

    <div class="console-footer">
      <div class="logs-count">共 {{ logs.length }} 条日志</div>
      <button
        v-if="!autoScroll && logs.length > 0"
        type="button"
        class="scroll-follow-btn"
        @click="scrollToBottom(true)"
      >
        <ChevronDown class="btn-icon" />
        <span>自动追随最新日志</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUpdated, nextTick } from 'vue';
import { Terminal, ChevronDown } from 'lucide-vue-next';

const props = defineProps<{
  logs: string[];
}>();

const logContainer = ref<HTMLElement | null>(null);
const autoScroll = ref(true);
const currentLevel = ref<'all' | 'steps' | 'metrics' | 'verbose'>('all');

const levels = [
  { value: 'all', label: '全部日志' },
  { value: 'steps', label: '研究步骤' },
  { value: 'metrics', label: '运行指标' },
  { value: 'verbose', label: 'LLM 审计' }
] as const;

const filteredLogs = computed(() => {
  if (currentLevel.value === 'all') return props.logs;
  
  return props.logs.filter(log => {
    const lower = log.toLowerCase();
    if (currentLevel.value === 'steps') {
      return !lower.includes('llm input') && !lower.includes('llm output') && !lower.includes('duration') && !lower.includes('tokens');
    }
    if (currentLevel.value === 'metrics') {
      return lower.includes('duration') || lower.includes('tokens') || lower.includes('tool_call') || lower.includes('耗时');
    }
    if (currentLevel.value === 'verbose') {
      return lower.includes('llm input') || lower.includes('llm output') || lower.includes('prompt') || lower.includes('context');
    }
    return true;
  });
});

const getLogTime = (log: string) => {
  const match = log.match(/^\[([^\]]+)\]/);
  return match ? match[1] : '';
};

const getLogClass = (log: string) => {
  const lower = log.toLowerCase();
  if (lower.includes('error') || lower.includes('fail') || lower.includes('出错')) return 'log-error';
  if (lower.includes('success') || lower.includes('完成') || lower.includes('complete')) return 'log-success';
  if (lower.includes('duration') || lower.includes('tokens') || lower.includes('耗时')) return 'log-metrics';
  if (lower.includes('llm input') || lower.includes('llm output')) return 'log-verbose';
  if (lower.includes('正在检索') || lower.includes('正在抓取') || lower.includes('正在阅读')) return 'log-tool';
  return 'log-step';
};

const formatLogMessage = (log: string) => {
  const message = log.replace(/^\[[^\]]+\]\s*/, '');
  return message.replace(
    /(https?:\/\/[^\s]+)/g,
    '<a href="$1" target="_blank" class="log-url">$1</a>'
  );
};

const handleScroll = () => {
  if (!logContainer.value) return;
  const { scrollTop, scrollHeight, clientHeight } = logContainer.value;
  autoScroll.value = scrollHeight - (scrollTop + clientHeight) < 15;
};

const scrollToBottom = (force = false) => {
  nextTick(() => {
    if (!logContainer.value) return;
    if (autoScroll.value || force) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  });
};

onUpdated(() => {
  scrollToBottom();
});
</script>

<style scoped>
.log-console {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: rgba(15, 23, 42, 0.65);
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
}

.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--glass-border);
  padding-bottom: 12px;
  margin-bottom: 12px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-icon {
  color: var(--color-secondary);
  width: 18px;
  height: 18px;
}

.header-title h3 {
  font-size: 0.9rem;
  color: var(--text-main);
  margin: 0;
  font-family: 'Outfit', sans-serif;
}

.filters {
  display: flex;
  gap: 6px;
}

.filter-btn {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--glass-border);
  color: var(--text-muted);
  font-size: 0.7rem;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-smooth);
}

.filter-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-main);
}

.filter-btn.active {
  background: rgba(52, 211, 153, 0.1);
  border-color: var(--color-secondary);
  color: var(--color-secondary);
}

.console-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px;
  display: flex;
  flex-direction: column;
}

.empty-logs {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-dark);
  font-size: 0.8rem;
  padding: 20px;
}

.pulse-text {
  animation: pulse 2s infinite ease-in-out;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.log-lines {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.log-line {
  font-size: 0.8rem;
  line-height: 1.4;
  word-break: break-all;
  display: flex;
  gap: 8px;
}

.log-time {
  color: var(--text-dark);
  flex-shrink: 0;
  user-select: none;
}

.log-message {
  flex: 1;
}

.log-step {
  color: var(--text-main);
}

.log-tool {
  color: var(--color-primary);
}

.log-metrics {
  color: var(--color-secondary);
}

.log-verbose {
  color: var(--text-muted);
}

.log-success {
  color: var(--color-success);
}

.log-error {
  color: var(--color-error);
}

:deep(.log-url) {
  color: var(--color-primary);
  text-decoration: underline;
}

:deep(.log-url:hover) {
  color: var(--color-secondary);
}

.console-footer {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--glass-border);
  padding-top: 10px;
  font-size: 0.7rem;
  color: var(--text-dark);
}

.scroll-follow-btn {
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.2);
  color: var(--color-primary);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: inherit;
  font-size: 0.7rem;
  transition: var(--transition-smooth);
}

.scroll-follow-btn:hover {
  background: rgba(56, 189, 248, 0.2);
  border-color: var(--color-primary);
}

.btn-icon {
  width: 12px;
  height: 12px;
}
</style>
