<template>
  <div class="query-tree glass-panel">
    <div class="tree-header">
      <Network class="network-icon" />
      <h3>知识探求脑图</h3>
    </div>
    <div class="tree-body">
      <svg v-if="treeData" class="tree-svg" viewBox="0 0 600 360" width="100%" height="100%">
        <!-- Lines -->
        <g class="tree-links">
          <line
            v-for="(link, idx) in links"
            :key="'link-' + idx"
            :x1="link.x1"
            :y1="link.y1"
            :x2="link.x2"
            :y2="link.y2"
            :class="['link-line', link.status]"
          />
        </g>
        <!-- Nodes -->
        <g class="tree-nodes">
          <g
            v-for="node in nodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
            :class="['node-group', node.type, node.status]"
          >
            <!-- Breathing glowing circle for active nodes -->
            <circle
              v-if="node.status === 'searching'"
              r="14"
              class="pulse-ring"
            />
            <circle
              :r="node.type === 'root' ? 8 : 6"
              class="node-circle"
            />
            <text
              :dx="node.type === 'root' ? 12 : 10"
              dy="4"
              class="node-text"
            >
              {{ truncateLabel(node.label) }}
            </text>
            <title>{{ node.label }} ({{ node.status }})</title>
          </g>
        </g>
      </svg>
      <div v-else class="empty-tree">
        <span>等待脑图数据生成...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Network } from 'lucide-vue-next';

const props = defineProps<{
  logs: string[];
  topic: string;
}>();

interface TreeNode {
  id: string;
  label: string;
  type: 'root' | 'subtopic' | 'query';
  status: 'pending' | 'searching' | 'completed';
  children: TreeNode[];
}

const truncateLabel = (lbl: string) => {
  if (lbl.length > 12) return lbl.substring(0, 10) + '...';
  return lbl;
};

// Build tree dynamically from steps logs
const treeData = computed<TreeNode | null>(() => {
  if (props.logs.length === 0) return null;

  const rootTopic = props.topic || '深度探索课题';
  const rootNode: TreeNode = {
    id: 'root',
    label: rootTopic,
    type: 'root',
    status: 'searching',
    children: []
  };

  const subtopicMap = new Map<string, TreeNode>();
  let currentSubtopic: TreeNode | null = null;

  for (const log of props.logs) {
    // 1. Detect sub-topics
    if (log.includes('开始研究子课题:') || log.includes('开始研究子方向:')) {
      const match = log.match(/子课题:\s*(.+)$/) || log.match(/子方向:\s*(.+)$/);
      if (match) {
        const title = match[1].trim();
        if (!subtopicMap.has(title)) {
          const subNode: TreeNode = {
            id: `sub-${subtopicMap.size}`,
            label: title,
            type: 'subtopic',
            status: 'completed',
            children: []
          };
          subtopicMap.set(title, subNode);
          rootNode.children.push(subNode);
        }
        currentSubtopic = subtopicMap.get(title) || null;
      }
    }
    
    // 2. Detect queries
    if (log.includes('正在检索:')) {
      const match = log.match(/正在检索:\s*'([^']+)'/);
      if (match && currentSubtopic) {
        const query = match[1].trim();
        const exists = currentSubtopic.children.some(c => c.label === query);
        if (!exists) {
          currentSubtopic.children.push({
            id: `q-${currentSubtopic.id}-${currentSubtopic.children.length}`,
            label: query,
            type: 'query',
            status: 'searching',
            children: []
          });
        }
      }
    }

    // 3. Mark completed queries
    if (log.includes('提取完成') || log.includes('抓取并提取')) {
      if (currentSubtopic) {
        currentSubtopic.children.forEach(c => {
          if (c.status === 'searching') c.status = 'completed';
        });
      }
    }
  }

  // Update root status
  if (props.logs.some(l => l.includes('报告合成完成') || l.includes('研究结束'))) {
    rootNode.status = 'completed';
    subtopicMap.forEach(s => s.status = 'completed');
  }

  return rootNode;
});

// Layout Nodes and Links
interface LayedNode extends TreeNode {
  x: number;
  y: number;
}

interface Link {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  status: 'pending' | 'searching' | 'completed';
}

const computedLayout = computed(() => {
  const nodes: LayedNode[] = [];
  const links: Link[] = [];

  const root = treeData.value;
  if (!root) return { nodes, links };

  const height = 360;
  
  // 1. Root Node
  const layedRoot: LayedNode = {
    ...root,
    x: 40,
    y: height / 2
  };
  nodes.push(layedRoot);

  const subtopics = root.children;
  const numSubs = subtopics.length;

  subtopics.forEach((sub, subIdx) => {
    // 2. Subtopic Nodes
    const subY = numSubs > 1 
      ? 40 + (subIdx * (height - 80)) / (numSubs - 1)
      : height / 2;
    
    const layedSub: LayedNode = {
      ...sub,
      x: 180,
      y: subY
    };
    nodes.push(layedSub);

    links.push({
      x1: layedRoot.x,
      y1: layedRoot.y,
      x2: layedSub.x,
      y2: layedSub.y,
      status: sub.status
    });

    const queries = sub.children;
    const numQueries = queries.length;

    queries.forEach((q, qIdx) => {
      // 3. Query Nodes
      const qY = numQueries > 1
        ? subY - 40 + (qIdx * 80) / (numQueries - 1)
        : subY;

      const layedQ: LayedNode = {
        ...q,
        x: 360,
        y: qY
      };
      nodes.push(layedQ);

      links.push({
        x1: layedSub.x,
        y1: layedSub.y,
        x2: layedQ.x,
        y2: layedQ.y,
        status: q.status
      });
    });
  });

  return { nodes, links };
});

const nodes = computed(() => computedLayout.value.nodes);
const links = computed(() => computedLayout.value.links);
</script>

<style scoped>
.query-tree {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: rgba(15, 23, 42, 0.45);
}

.tree-header {
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--glass-border);
  padding-bottom: 12px;
  margin-bottom: 12px;
}

.network-icon {
  color: var(--color-primary);
  width: 18px;
  height: 18px;
}

.tree-header h3 {
  font-size: 0.9rem;
  color: var(--text-main);
  margin: 0;
  font-family: 'Outfit', sans-serif;
}

.tree-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 250px;
}

.tree-svg {
  overflow: visible;
}

.empty-tree {
  color: var(--text-dark);
  font-size: 0.8rem;
  animation: pulse 2s infinite ease-in-out;
}

/* Link line styles */
.link-line {
  stroke-width: 1.5;
  fill: none;
  stroke: var(--text-dark);
  opacity: 0.2;
  transition: var(--transition-smooth);
}

.link-line.searching {
  stroke: var(--color-primary);
  opacity: 0.6;
  stroke-dasharray: 4, 4;
  animation: dash 1s linear infinite;
}

.link-line.completed {
  stroke: var(--color-secondary);
  opacity: 0.5;
}

@keyframes dash {
  to {
    stroke-dashoffset: -8;
  }
}

/* Node styles */
.node-circle {
  fill: rgba(30, 41, 59, 0.9);
  stroke: var(--text-dark);
  stroke-width: 2px;
  transition: var(--transition-smooth);
}

.node-group:hover .node-circle {
  transform: scale(1.2);
}

.node-text {
  font-size: 10px;
  fill: var(--text-muted);
  font-family: 'Inter', sans-serif;
  user-select: none;
  pointer-events: none;
}

/* State overrides */
.root .node-circle {
  stroke: var(--color-primary);
  fill: rgba(56, 189, 248, 0.1);
}

.subtopic .node-circle {
  stroke: var(--color-accent);
}

.completed .node-circle {
  stroke: var(--color-secondary);
  fill: rgba(52, 211, 153, 0.2);
}

.completed .node-text {
  fill: var(--text-main);
}

.searching .node-circle {
  stroke: var(--color-primary);
  fill: rgba(56, 189, 248, 0.2);
}

.searching .node-text {
  fill: var(--color-primary);
}

/* Breathing Ring anim */
.pulse-ring {
  fill: none;
  stroke: var(--color-primary);
  stroke-width: 1px;
  opacity: 0;
  animation: ring-pulse 1.5s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}

@keyframes ring-pulse {
  0% {
    r: 6px;
    opacity: 0.8;
  }
  100% {
    r: 18px;
    opacity: 0;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
</style>
