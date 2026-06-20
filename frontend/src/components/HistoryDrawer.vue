<template>
  <Transition name="drawer">
    <div v-if="isOpen" class="drawer-overlay" @click.self="$emit('close')">
      <div class="drawer-content glass-panel">
        <div class="drawer-header">
          <div class="header-title">
            <History class="history-icon" />
            <h2>历史研究报告</h2>
          </div>
          <button type="button" class="close-btn" @click="$emit('close')">
            <X />
          </button>
        </div>

        <div v-if="loading" class="drawer-loader">
          <div class="spinner"></div>
          <p>正在获取历史报告...</p>
        </div>

        <div v-else class="drawer-body">
          <div v-if="reports.length === 0" class="empty-history">
            <BookOpen class="empty-icon" />
            <p>暂无历史研究记录</p>
          </div>
          <div v-else class="reports-list">
            <div
              v-for="rep in reports"
              :key="rep.id"
              :class="['report-card', { active: activeId === rep.id }]"
              @click="handleSelect(rep.id)"
            >
              <div class="card-title">{{ rep.topic }}</div>
              <div class="card-meta">
                <span>深度: {{ rep.max_depth }}</span>
                <span>广度: {{ rep.max_breadth }}</span>
                <span>事实: {{ rep.facts_count }}</span>
                <span>来源: {{ rep.sources_count }}</span>
              </div>
              <div class="card-footer">
                <span class="card-date">{{ formatDate(rep.created_at) }}</span>
                <button
                  type="button"
                  class="delete-btn"
                  @click.stop="handleDelete(rep.id)"
                  title="删除记录"
                >
                  <Trash2 class="delete-icon" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { History, X, BookOpen, Trash2 } from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
  activeId: string | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'select', reportId: string): void;
  (e: 'deleted', reportId: string): void;
}>();

interface ReportMeta {
  id: string;
  topic: string;
  max_depth: number;
  max_breadth: number;
  created_at: string;
  facts_count: number;
  sources_count: number;
}

const reports = ref<ReportMeta[]>([]);
const loading = ref(false);

const fetchReports = async () => {
  loading.value = true;
  try {
    const res = await fetch('/api/reports');
    if (res.ok) {
      reports.value = await res.json();
    }
  } catch (e) {
    console.error('Failed to fetch historical reports', e);
  } finally {
    loading.value = false;
  }
};

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    fetchReports();
  }
});

const formatDate = (dateStr: string) => {
  try {
    const d = new Date(dateStr);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  } catch {
    return dateStr;
  }
};

const handleSelect = (id: string) => {
  emit('select', id);
  emit('close');
};

const handleDelete = async (id: string) => {
  if (!confirm('您确定要删除该篇报告吗？该操作不可撤销。')) return;

  try {
    const res = await fetch(`/api/reports/${id}`, {
      method: 'DELETE'
    });
    if (res.ok) {
      reports.value = reports.value.filter(r => r.id !== id);
      emit('deleted', id);
    }
  } catch (e) {
    console.error('Failed to delete report', e);
  }
};
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  z-index: 1000;
}

.drawer-content {
  position: absolute;
  top: 0;
  left: 0;
  width: 380px;
  height: 100%;
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  border-left: none;
  display: flex;
  flex-direction: column;
  padding: 24px;
  background: rgba(15, 23, 42, 0.85);
  box-shadow: 10px 0 30px rgba(0, 0, 0, 0.5);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.history-icon {
  color: var(--color-primary);
  width: 20px;
  height: 20px;
}

.header-title h2 {
  font-size: 1.15rem;
  color: var(--text-main);
  margin: 0;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-smooth);
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-main);
}

.drawer-loader {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-muted);
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

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--text-dark);
  text-align: center;
}

.empty-icon {
  width: 36px;
  height: 36px;
  opacity: 0.5;
  margin-bottom: 12px;
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.report-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: 14px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.report-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(56, 189, 248, 0.3);
  transform: translateX(4px);
}

.report-card.active {
  background: rgba(56, 189, 248, 0.08);
  border-color: var(--color-primary);
}

.card-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-bottom: 10px;
}

.card-meta span {
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  padding-top: 8px;
}

.card-date {
  font-size: 0.7rem;
  color: var(--text-dark);
}

.delete-btn {
  background: transparent;
  border: none;
  color: var(--text-dark);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-smooth);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  color: var(--color-error);
}

.delete-icon {
  width: 14px;
  height: 14px;
}

/* Drawer Transitions */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-enter-active .drawer-content,
.drawer-leave-active .drawer-content {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .drawer-content {
  transform: translateX(-100%);
}

.drawer-leave-to .drawer-content {
  transform: translateX(-100%);
}
</style>
