<script setup lang="ts">
import { ref, computed } from 'vue'
import { nodes, edges } from './PipelineData'
import type { ProvenanceNode, ProvenanceEdge } from './PipelineData'

const hoveredNode = ref<string | null>(null)

const stageLabels = ['Data Sources', 'Spatial Grids', 'Derived Datasets', 'What You See']

// Layout constants — top-to-bottom flow
const nodeWidth = 160
const nodeHeight = 72
const nodeGapX = 14
const rowGap = 56
const headerHeight = 22
const paddingTop = 12
const paddingX = 10
const legendHeight = 38

// Widest row is 4 nodes
const maxRowWidth = 4 * nodeWidth + 3 * nodeGapX

// Group nodes by stage (row)
const nodesByStage = computed(() => {
  const grouped: ProvenanceNode[][] = [[], [], [], []]
  for (const node of nodes) grouped[node.stage].push(node)
  return grouped
})

// Row Y positions (top of header text for each stage)
function rowY(stage: number): number {
  return paddingTop + stage * (headerHeight + nodeHeight + rowGap)
}

// Compute node positions — centered horizontally per row
const nodePositions = computed(() => {
  const positions = new Map<string, { x: number, y: number }>()
  for (let stage = 0; stage < 4; stage++) {
    const stageNodes = nodesByStage.value[stage] ?? []
    const rowWidth = stageNodes.length * nodeWidth + (stageNodes.length - 1) * nodeGapX
    const offsetX = paddingX + (maxRowWidth - rowWidth) / 2
    const nodesY = rowY(stage) + headerHeight + 4
    for (let i = 0; i < stageNodes.length; i++) {
      positions.set(stageNodes[i]!.id, {
        x: offsetX + i * (nodeWidth + nodeGapX),
        y: nodesY
      })
    }
  }
  return positions
})

const svgWidth = computed(() => maxRowWidth + paddingX * 2)
const svgHeight = computed(() => rowY(3) + headerHeight + 4 + nodeHeight + legendHeight)

// Edge path: exits bottom-center, enters top-center
function edgePath(edge: ProvenanceEdge): string {
  const fromPos = nodePositions.value.get(edge.from)
  const toPos = nodePositions.value.get(edge.to)
  if (!fromPos || !toPos) return ''

  const x1 = fromPos.x + nodeWidth / 2
  const y1 = fromPos.y + nodeHeight
  const x2 = toPos.x + nodeWidth / 2
  const y2 = toPos.y

  const dy = y2 - y1
  return `M ${x1} ${y1} C ${x1} ${y1 + dy * 0.45}, ${x2} ${y2 - dy * 0.45}, ${x2} ${y2}`
}

function edgeStroke(edge: ProvenanceEdge): string {
  if (edge.type === 'h3') return 'var(--color-forest-500)'
  if (edge.type === 'grid') return 'var(--color-density-5)'
  return 'var(--color-border)'
}

function edgeOpacity(edge: ProvenanceEdge): number {
  if (!hoveredNode.value) return 0.4
  if (edge.from === hoveredNode.value || edge.to === hoveredNode.value) return 0.85
  return 0.1
}

function nodeStroke(node: ProvenanceNode): string {
  switch (node.type) {
    case 'source': return 'var(--color-density-4)'
    case 'grid': return 'var(--color-forest-500)'
    case 'derived': return 'var(--color-forest-300)'
    case 'output': return 'var(--color-density-2)'
  }
}

function nodeFill(node: ProvenanceNode): string {
  switch (node.type) {
    case 'source': return 'var(--color-density-1)'
    case 'grid': return 'var(--color-forest-50)'
    case 'derived': return 'var(--color-parchment)'
    case 'output': return 'var(--color-density-1)'
  }
}

function nodeOpacity(node: ProvenanceNode): number {
  if (!hoveredNode.value) return 1
  if (node.id === hoveredNode.value) return 1
  const connected = edges.some(
    e =>
      (e.from === hoveredNode.value && e.to === node.id)
      || (e.to === hoveredNode.value && e.from === node.id)
  )
  return connected ? 1 : 0.35
}

function wrapText(text: string, maxChars: number): string[] {
  if (text.length <= maxChars) return [text]
  const breakAt = text.lastIndexOf(' ', maxChars)
  if (breakAt === -1) return [text]
  return [text.slice(0, breakAt), text.slice(breakAt + 1)]
}
</script>

<template>
  <div class="my-10">
    <svg
      :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
      width="100%"
      role="img"
      aria-label="Data provenance diagram showing how satellite data flows through processing stages to the visualizations on this site"
    >
      <!-- Row headers -->
      <text
        v-for="(label, i) in stageLabels"
        :key="'header-' + i"
        :x="paddingX + maxRowWidth / 2"
        :y="rowY(i) + 14"
        text-anchor="middle"
        class="fill-espresso dark:fill-dark-espresso"
        font-family="var(--font-heading)"
        font-size="13"
        font-weight="600"
      >
        {{ label }}
      </text>

      <!-- Edges (rendered below nodes) -->
      <path
        v-for="(edge, i) in edges"
        :key="'edge-' + i"
        :d="edgePath(edge)"
        fill="none"
        :stroke="edgeStroke(edge)"
        :stroke-opacity="edgeOpacity(edge)"
        stroke-width="1.5"
        stroke-linecap="round"
        class="transition-[stroke-opacity] duration-200"
      />

      <!-- Nodes -->
      <g
        v-for="node in nodes"
        :key="node.id"
        :transform="`translate(${nodePositions.get(node.id)?.x ?? 0}, ${nodePositions.get(node.id)?.y ?? 0})`"
        :opacity="nodeOpacity(node)"
        class="cursor-default transition-opacity duration-200"
        @mouseenter="hoveredNode = node.id"
        @mouseleave="hoveredNode = null"
      >
        <rect
          :width="nodeWidth"
          :height="nodeHeight"
          rx="6"
          :fill="nodeFill(node)"
          :stroke="nodeStroke(node)"
          stroke-width="1.5"
        />
        <!-- Label -->
        <text
          :x="nodeWidth / 2"
          y="20"
          text-anchor="middle"
          font-family="var(--font-sans)"
          font-size="11"
          font-weight="600"
          class="fill-espresso dark:fill-dark-espresso"
        >
          {{ node.label }}
        </text>
        <!-- Description -->
        <text
          :x="nodeWidth / 2"
          y="35"
          text-anchor="middle"
          font-family="var(--font-sans)"
          font-size="8.5"
          font-weight="300"
          class="fill-body dark:fill-dark-body"
        >
          <tspan
            v-for="(line, li) in wrapText(node.description, 38)"
            :key="li"
            :x="nodeWidth / 2"
            :dy="li === 0 ? 0 : 11"
          >
            {{ line }}
          </tspan>
        </text>
        <!-- Source citation -->
        <text
          v-if="node.source"
          :x="nodeWidth / 2"
          :y="nodeHeight - 7"
          text-anchor="middle"
          font-family="var(--font-sans)"
          font-size="7.5"
          font-style="italic"
          class="fill-data dark:fill-dark-data"
          opacity="0.7"
        >
          {{ node.source }}
        </text>
      </g>

      <!-- Legend -->
      <g :transform="`translate(${paddingX + maxRowWidth - 170}, ${svgHeight - legendHeight + 6})`">
        <line
          x1="0"
          y1="8"
          x2="16"
          y2="8"
          stroke="var(--color-forest-500)"
          stroke-width="1.5"
        />
        <text
          x="22"
          y="11"
          font-family="var(--font-sans)"
          font-size="8.5"
          class="fill-body dark:fill-dark-body"
        >
          H3 hexagonal path
        </text>
        <line
          x1="90"
          y1="8"
          x2="106"
          y2="8"
          stroke="var(--color-density-5)"
          stroke-width="1.5"
        />
        <text
          x="112"
          y="11"
          font-family="var(--font-sans)"
          font-size="8.5"
          class="fill-body dark:fill-dark-body"
        >
          1 km grid path
        </text>
      </g>
    </svg>
  </div>
</template>
