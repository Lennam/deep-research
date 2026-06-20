<template>
  <div class="config-panel glass-panel">
    <div class="panel-header">
      <div class="logo">
        <Sparkles class="logo-icon" />
        <h2>Deep Research</h2>
      </div>
      <button type="button" class="history-btn" @click="$emit('open-history')" title="查看历史报告">
        <History />
      </button>
    </div>

    <form @submit.prevent="handleSubmit" class="panel-body">
      <div class="input-group">
        <label for="topic">研究课题</label>
        <textarea
          id="topic"
          v-model="form.topic"
          placeholder="请输入您想要研究的主题或问题，例如：'大语言模型智能体状态管理技术现状与发展趋势'..."
          class="glass-input"
          :disabled="isRunning"
          required
        ></textarea>
      </div>

      <div class="input-group">
        <div class="slider-header">
          <label>探索深度 (Depth): {{ form.max_depth }}</label>
          <span class="info-badge" :title="depthTooltip">提示</span>
        </div>
        <input
          type="range"
          v-model.number="form.max_depth"
          min="1"
          max="5"
          step="1"
          class="glass-slider"
          :disabled="isRunning"
        />
        <div class="slider-labels">
          <span>简单</span>
          <span>标准</span>
          <span>极深</span>
        </div>
      </div>

      <div class="input-group">
        <div class="slider-header">
          <label>探索广度 (Breadth): {{ form.max_breadth }}</label>
          <span class="info-badge" :title="breadthTooltip">提示</span>
        </div>
        <input
          type="range"
          v-model.number="form.max_breadth"
          min="1"
          max="10"
          step="1"
          class="glass-slider"
          :disabled="isRunning"
        />
        <div class="slider-labels">
          <span>窄</span>
          <span>中等</span>
          <span>宽</span>
        </div>
      </div>

      <div class="input-group">
        <label>数据源路由模式</label>
        <div class="mode-select">
          <button
            type="button"
            v-for="mode in modes"
            :key="mode.value"
            :class="['mode-btn', { active: form.search_mode === mode.value }]"
            :disabled="isRunning"
            @click="form.search_mode = mode.value"
          >
            <component :is="mode.icon" class="btn-icon" />
            <span>{{ mode.label }}</span>
          </button>
        </div>
      </div>

      <div class="action-container">
        <button
          v-if="!isRunning"
          type="submit"
          class="submit-btn"
        >
          <Search class="btn-icon animate-pulse" />
          <span>开始深度研究</span>
        </button>
        <button
          v-else
          type="button"
          class="stop-btn"
          @click="$emit('stop')"
        >
          <StopCircle class="btn-icon" />
          <span>中止探索 (Cancel)</span>
        </button>
      </div>
    </form>

    <!-- 运行指标面板 -->
    <div v-if="isRunning || currentDepth > 0" class="metrics-panel">
      <h3>探索实时指标</h3>
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-val">{{ currentDepth }} / {{ form.max_depth }}</div>
          <div class="metric-lbl">当前深度</div>
        </div>
        <div class="metric-card">
          <div class="metric-val">{{ sourcesCount }}</div>
          <div class="metric-lbl">分析源链接</div>
        </div>
        <div class="metric-card">
          <div class="metric-val">{{ factsCount }}</div>
          <div class="metric-lbl">提炼事实数</div>
        </div>
        <div class="metric-card">
          <div class="metric-val">{{ costEstimate }}</div>
          <div class="metric-lbl">预计花费</div>
        </div>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { Sparkles, History, Search, StopCircle, Globe, GraduationCap, Layers } from 'lucide-vue-next';

const props = defineProps<{
  isRunning: boolean;
  currentTaskId: string | null;
  currentDepth: number;
  sourcesCount: number;
  factsCount: number;
}>();

const emit = defineEmits<{
  (e: 'start', payload: { topic: string, max_depth: number, max_breadth: number, search_mode: string }): void;
  (e: 'stop'): void;
  (e: 'open-history'): void;
}>();

const form = ref({
  topic: '',
  max_depth: 2,
  max_breadth: 3,
  search_mode: 'all'
});

const modes = [
  { value: 'all', label: '全能路由', icon: Layers },
  { value: 'web', label: '网页优先', icon: Globe },
  { value: 'academic', label: '学术优先', icon: GraduationCap }
];

const depthTooltip = 'Depth 控制递归层级。深度越高，智能体会基于第一轮提炼的新线索，发起更深次的搜索和事实分析。推荐级别为 2。';
const breadthTooltip = 'Breadth 控制每一轮探索的并发子查询数量。广度越大，覆盖的课题面越宽，消耗的 API 配额与时间相应增加。';

const costEstimate = computed(() => {
  if (props.factsCount === 0 && props.sourcesCount === 0) return '$0.00';
  const estimate = (props.sourcesCount * 0.02) + (props.factsCount * 0.015);
  return `$${estimate.toFixed(2)}`;
});

const progressPercent = computed(() => {
  if (!props.isRunning) return 100;
  if (form.value.max_depth === 0) return 0;
  return Math.min(Math.round((props.currentDepth / form.value.max_depth) * 100), 95);
});

const handleSubmit = () => {
  if (form.value.topic.trim()) {
    emit('start', { ...form.value });
  }
};
</script>

<style scoped>
.config-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  color: var(--color-primary);
  width: 24px;
  height: 24px;
}

.panel-header h2 {
  font-size: 1.25rem;
  background: linear-gradient(to right, var(--color-primary), var(--color-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}

.history-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--glass-border);
  color: var(--text-main);
  border-radius: var(--radius-sm);
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.history-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: var(--color-primary);
  transform: translateY(-2px);
}

.panel-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-muted);
}

textarea {
  min-height: 110px;
  resize: vertical;
  line-height: 1.5;
  font-size: 0.9rem;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-badge {
  font-size: 0.7rem;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--glass-border);
  color: var(--text-muted);
  padding: 2px 6px;
  border-radius: 12px;
  cursor: help;
  transition: var(--transition-smooth);
}

.info-badge:hover {
  background: rgba(56, 189, 248, 0.15);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.glass-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.1);
  outline: none;
  cursor: pointer;
}

.glass-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  box-shadow: 0 0 8px var(--color-primary);
  cursor: pointer;
  transition: transform 0.1s ease;
}

.glass-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: var(--text-dark);
  padding: 0 2px;
}

.mode-select {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 4px;
}

.mode-btn {
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  padding: 10px 4px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  transition: var(--transition-smooth);
}

.mode-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.2);
  color: var(--text-main);
}

.mode-btn.active {
  background: rgba(56, 189, 248, 0.1);
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.15);
}

.mode-btn .btn-icon {
  width: 18px;
  height: 18px;
}

.mode-btn span {
  font-size: 0.75rem;
  font-weight: 500;
}

.action-container {
  margin-top: 10px;
}

.submit-btn, .stop-btn {
  width: 100%;
  padding: 14px;
  border-radius: var(--radius-md);
  border: none;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.submit-btn {
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  color: #020617;
  box-shadow: 0 4px 20px rgba(56, 189, 248, 0.3);
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(56, 189, 248, 0.45);
}

.stop-btn {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: var(--color-error);
}

.stop-btn:hover {
  background: rgba(239, 68, 68, 0.25);
  border-color: var(--color-error);
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.2);
}

.btn-icon {
  width: 18px;
  height: 18px;
}

.animate-pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .5; }
}

.metrics-panel {
  margin-top: auto;
  border-top: 1px solid var(--glass-border);
  padding-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metrics-panel h3 {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.metric-card {
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: 10px;
  text-align: center;
}

.metric-val {
  font-family: 'Outfit', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-primary);
}

.metric-lbl {
  font-size: 0.65rem;
  color: var(--text-dark);
  margin-top: 2px;
}

.progress-bar-container {
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 4px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  transition: width 0.4s ease;
}
</style>
