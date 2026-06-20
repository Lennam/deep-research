import { ref } from 'vue';
import type { LogEvent, StateUpdateEvent } from '../types';

export function useSSE() {
  const isConnecting = ref(false);
  const currentTaskId = ref<string | null>(null);
  const eventSource = ref<EventSource | null>(null);

  // States
  const stateLogs = ref<string[]>([]);
  const extractedFactsCount = ref(0);
  const sourcesCount = ref(0);
  const currentDepth = ref(0);
  const finalReport = ref<string>('');

  const connectSSE = (
    taskId: string,
    onComplete: (report: string) => void,
    onError: (err: string) => void
  ) => {
    currentTaskId.value = taskId;
    isConnecting.value = true;
    stateLogs.value = [];
    finalReport.value = '';
    extractedFactsCount.value = 0;
    sourcesCount.value = 0;
    currentDepth.value = 0;

    // Use Vite dev server proxy path
    const sseUrl = `/api/research/stream/${taskId}`;
    eventSource.value = new EventSource(sseUrl);

    eventSource.value.addEventListener('log', (event: any) => {
      try {
        const data: LogEvent = JSON.parse(event.data);
        const timeStr = new Date(data.timestamp * 1000).toLocaleTimeString();
        stateLogs.value.push(`[${timeStr}] ${data.message}`);
      } catch (e) {
        console.error('Failed to parse log event', e);
      }
    });

    eventSource.value.addEventListener('state_update', (event: any) => {
      try {
        const data: StateUpdateEvent = JSON.parse(event.data);
        currentDepth.value = data.current_depth;
        sourcesCount.value = data.sources_count;
        extractedFactsCount.value = data.facts_count;
      } catch (e) {
        console.error('Failed to parse state_update event', e);
      }
    });

    eventSource.value.addEventListener('complete', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        finalReport.value = data.report;
        isConnecting.value = false;
        closeSSE();
        onComplete(data.report);
      } catch (e) {
        console.error('Failed to parse complete event', e);
        onError('Completed but report format was invalid.');
        isConnecting.value = false;
        closeSSE();
      }
    });

    eventSource.value.addEventListener('error', (event: any) => {
      if (event.data) {
        try {
          const data = JSON.parse(event.data);
          onError(data.message || '任务执行错误');
        } catch (e) {
          onError('任务执行异常');
        }
      } else {
        onError('网络长连接意外中断或任务被中止');
      }
      isConnecting.value = false;
      closeSSE();
    });
  };

  const closeSSE = () => {
    if (eventSource.value) {
      eventSource.value.close();
      eventSource.value = null;
    }
  };

  return {
    isConnecting,
    currentTaskId,
    stateLogs,
    currentDepth,
    sourcesCount,
    extractedFactsCount,
    finalReport,
    connectSSE,
    closeSSE
  };
}
