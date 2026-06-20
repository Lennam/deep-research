<template>
  <div class="app-container">
    <!-- Configuration Sidebar -->
    <aside class="sidebar-layout no-print">
      <ConfigPanel
        :is-running="isConnecting"
        :current-task-id="currentTaskId"
        :current-depth="currentDepth"
        :sources-count="sourcesCount"
        :facts-count="extractedFactsCount"
        @start="handleStart"
        @stop="handleStop"
        @open-history="historyOpen = true"
      />
    </aside>

    <!-- Center Workspace (Query Tree and Logs Console) -->
    <main class="workspace-layout no-print">
      <div class="workspace-top">
        <QueryTree :logs="stateLogs" :topic="topic" />
      </div>
      <div class="workspace-bottom">
        <LogConsole :logs="stateLogs" />
      </div>
    </main>

    <!-- Right Report Viewer Panel -->
    <section class="report-layout">
      <ReportViewer
        :content="reportContent"
        :sources="sources"
        :topic="topic"
        :is-running="isConnecting"
      />
    </section>

    <!-- History Reports Drawer Overlay -->
    <HistoryDrawer
      :is-open="historyOpen"
      :active-id="activeReportId"
      @close="historyOpen = false"
      @select="handleLoadHistory"
      @deleted="handleHistoryDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import ConfigPanel from './components/ConfigPanel.vue';
import LogConsole from './components/LogConsole.vue';
import QueryTree from './components/QueryTree.vue';
import ReportViewer from './components/ReportViewer.vue';
import HistoryDrawer from './components/HistoryDrawer.vue';
import { useSSE } from './composables/useSSE';

const historyOpen = ref(false);
const activeReportId = ref<string | null>(null);

// Main research state
const topic = ref('');
const reportContent = ref('');
const sources = ref<Array<{ url: string; title: string; snippet?: string }>>([]);

const {
  isConnecting,
  currentTaskId,
  stateLogs,
  currentDepth,
  sourcesCount,
  extractedFactsCount,
  connectSSE,
  closeSSE
} = useSSE();

const handleStart = async (config: { topic: string; max_depth: number; max_breadth: number; search_mode: string }) => {
  // Clear previous research state
  topic.value = config.topic;
  reportContent.value = '';
  sources.value = [];
  activeReportId.value = null;
  
  try {
    const res = await fetch('/api/research/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        topic: config.topic,
        max_depth: config.max_depth,
        max_breadth: config.max_breadth,
        search_mode: config.search_mode
      })
    });
    
    if (res.ok) {
      const data = await res.json();
      const taskId = data.task_id;
      
      // Connect to SSE stream
      connectSSE(
        taskId,
        // On Complete
        (report) => {
          reportContent.value = report;
          activeReportId.value = taskId;
          // Refresh report details (sources etc) from DB after completion to ensure sync
          handleLoadHistory(taskId);
        },
        // On Error
        (err) => {
          alert(`研究任务中止: ${err}`);
        }
      );
    } else {
      const errData = await res.json();
      alert(`启动失败: ${errData.detail || '服务错误'}`);
    }
  } catch (e) {
    console.error('Failed to start research task', e);
    alert('启动网络请求失败，请确保后端服务已正常运行。');
  }
};

const handleStop = async () => {
  if (!currentTaskId.value) return;
  
  try {
    const res = await fetch(`/api/research/stop/${currentTaskId.value}`, {
      method: 'POST'
    });
    if (res.ok) {
      closeSSE();
      isConnecting.value = false;
      stateLogs.value.push(`[${new Date().toLocaleTimeString()}] 研究任务已被用户主动中止。`);
    }
  } catch (e) {
    console.error('Failed to stop research task', e);
  }
};

const handleLoadHistory = async (reportId: string) => {
  try {
    const res = await fetch(`/api/reports/${reportId}`);
    if (res.ok) {
      const data = await res.json();
      topic.value = data.topic;
      reportContent.value = data.report_content;
      sources.value = data.state_json?.sources || [];
      activeReportId.value = reportId;
      
      // Reset logs so console doesn't show confusing logs from other tasks
      stateLogs.value = [`[历史记录] 成功加载课题 "${data.topic}" 的研究报告`];
    }
  } catch (e) {
    console.error('Failed to load historical report details', e);
  }
};

const handleHistoryDeleted = (id: string) => {
  if (activeReportId.value === id) {
    topic.value = '';
    reportContent.value = '';
    sources.value = [];
    activeReportId.value = null;
    stateLogs.value = [];
  }
};
</script>

<style>
/* App Layout grids */
.app-container {
  display: grid;
  grid-template-columns: 340px 1fr 1.2fr;
  gap: 20px;
  height: 100vh;
  padding: 20px;
  overflow: hidden;
}

.sidebar-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.workspace-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.workspace-top {
  flex: 1.1;
  min-height: 0;
}

.workspace-bottom {
  flex: 0.9;
  min-height: 0;
}

.report-layout {
  height: 100%;
  min-width: 0;
}

/* Responsiveness overrides */
@media (max-width: 1200px) {
  .app-container {
    grid-template-columns: 300px 1fr;
    grid-template-rows: 1fr 1fr;
  }
  .report-layout {
    grid-column: 2;
    grid-row: 1 / span 2;
  }
}

@media (max-width: 768px) {
  .app-container {
    display: flex;
    flex-direction: column;
    height: auto;
    overflow-y: auto;
  }
  .sidebar-layout,
  .workspace-layout,
  .report-layout {
    height: 600px;
  }
}

@media print {
  .app-container {
    display: block !important;
    padding: 0 !important;
    height: auto !important;
  }
  .report-layout {
    height: auto !important;
  }
}
</style>
