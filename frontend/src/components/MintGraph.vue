<template>
  <q-card class="bg-dark">
    <q-card-section class="bg-dark text-light">
      <h2 class="text-h6">Mint Graph</h2>
    </q-card-section>
    <div class="mint-graph-container">
      <svg ref="svgRef"></svg>
      <div v-if="!isLoaded" class="load-button-container">
        <q-btn
          label="Load Graph"
          outline
          color="primary"
          @click="loadGraph"
          :loading="loading"
        />
      </div>
      <q-spinner v-if="loading" color="primary" size="50px" class="q-my-md" />
      <div v-if="error" class="text-negative q-pa-md">
        {{ error }}
      </div>
      <div ref="tooltip" class="tooltip" style="opacity: 0;"></div>
    </div>

    <!-- Mint Swap Stats Dialog -->
    <MintSwapStats
      v-if="selectedMint"
      v-model="showSwapStats"
      :mint="selectedMint"
    />
  </q-card>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { MintGraph, MintRead } from 'src/models/mint';
import { getMintGraph } from 'src/services/mintService';
import * as d3 from 'd3';
import MintSwapStats from './MintSwapStats.vue';

interface GraphNode extends d3.SimulationNodeDatum {
  id: number;
  name?: string;
  url?: string;
  balance: number;
  state: string;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  count: number;
  total_amount: number;
  state: string;
}

export default defineComponent({
  name: 'MintGraph',
  components: {
    MintSwapStats
  },
  setup() {
    const svgRef = ref<SVGSVGElement | null>(null);
    const tooltipRef = ref<HTMLDivElement | null>(null);
    const mintGraph = ref<MintGraph | null>(null);
    const loading = ref(false);
    const error = ref('');
    const isLoaded = ref(false);
    const showSwapStats = ref(false);
    const selectedMint = ref<MintRead | null>(null);
    let simulation: d3.Simulation<GraphNode, GraphLink> | null = null;

    const loadGraph = async () => {
      loading.value = true;
      error.value = '';
      try {
        mintGraph.value = await getMintGraph();
        renderGraph();
        isLoaded.value = true;
      } catch (err) {
        error.value = 'Error fetching mint graph.';
        console.error(err);
      } finally {
        loading.value = false;
      }
    };

    const renderGraph = () => {
      if (!mintGraph.value || !svgRef.value) return;

      const nodes: GraphNode[] = mintGraph.value.nodes.map((node) => ({
        ...node,
      }));

      const nodeById = new Map<number, GraphNode>(nodes.map((node) => [node.id, node]));

      const links: GraphLink[] = mintGraph.value.edges.map((edge) => {
        const sourceNode = nodeById.get(edge.from_id);
        const targetNode = nodeById.get(edge.to_id);

        if (!sourceNode || !targetNode) {
          console.error('Invalid edge: source or target node not found');
          return null;
        }

        return {
          source: sourceNode,
          target: targetNode,
          count: edge.count,
          total_amount: edge.total_amount,
          state: edge.state,
        } as GraphLink;
      }).filter((link): link is GraphLink => link !== null);

      d3.select(svgRef.value).selectAll('*').remove();

      const width = svgRef.value.clientWidth || 800;
      const height = svgRef.value.clientHeight || 400;

      const svg = d3.select(svgRef.value)
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('viewBox', `0 0 ${width} ${height}`)
        .attr('preserveAspectRatio', 'xMidYMid meet');

      // Add zoom behavior
      const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          container.attr('transform', event.transform);
        });

      // Create a container for all elements
      const container = svg.append('g');

      // Apply zoom behavior to SVG
      svg.call(zoom as any);

      // Adjust force simulation parameters for smaller screens
      const forceStrength = width < 600 ? -100 : -200; // Reduce force on small screens
      const linkDistance = width < 600 ? 150 : 250; // Reduce link distance on small screens

      // Define arrowhead markers
      svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 25) // Adjust based on link distance
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 2)
        .attr('markerHeight', 2)
        .attr('xoverflow', 'visible')
        .append('svg:path')
        .attr('d', 'M 0,-5 L 10,0 L 0,5') // Arrow shape
        .attr('fill', '#aaa')
        .style('stroke', 'none');

      const tooltip = d3.select(tooltipRef.value);

      simulation = d3.forceSimulation<GraphNode, GraphLink>(nodes)
          .force('link', d3.forceLink<GraphNode, GraphLink>(links)
          .id((d) => d.id.toString())
          .distance(linkDistance)
          .strength((d) => Math.log(d.count) / 1000)
        )
        .force('charge', d3.forceManyBody().strength(forceStrength))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('x', d3.forceX(width / 2).strength(0.01))
        .force('y', d3.forceY(height / 2).strength(0.05))
        .on('tick', ticked);

      const link = container.append('g')
        .attr('class', 'links')
        .selectAll('path')
        .data(links)
        .enter().append('path')
        .attr('stroke-width', (d) => Math.log(d.count)/2)
        .attr('stroke', (d) => d.state === 'OK' ? '#7b7' : '#a66')
        .attr('stroke-opacity', 0.4)
        .attr('fill', 'none')
        .attr('marker-end', 'url(#arrowhead)') // Attach the marker to the end of the path
        // Tooltip events for edges
        .on('mouseover', (event, d) => {
          tooltip
            .style('opacity', 1)
            .html(`<strong>Edge:</strong><br>Count: ${d.count}<br>Total Amount: ${d.total_amount}`);
        })
        .on('mousemove', (event) => {
          tooltip
            .style('left', `${event.clientX + 10}px`)
            .style('top', `${event.clientY - 28}px`);
        })
        .on('mouseout', () => {
          tooltip.style('opacity', 0);
        });

      const node = container.append('g')
        .attr('class', 'nodes')
        .selectAll('circle')
        .data(nodes)
        .enter().append('circle')
        .attr('r', 10)
        .attr('fill', (d) => getStateColor(d.state))
        .attr('stroke', '#000')
        .call(drag(simulation))
        // Tooltip events for nodes
        .on('mouseover', (event, d) => {
          tooltip
            .style('opacity', 1)
            .html(`<strong>Mint:</strong><br>Name: ${d.name || d.url}<br>Balance: ${d.balance}`);
        })
        .on('mousemove', (event) => {
          tooltip
            .style('left', `${event.clientX + 10}px`)
            .style('top', `${event.clientY - 28}px`);
        })
        .on('mouseout', () => {
          tooltip.style('opacity', 0);
        })
        // Add click handler for nodes
        .on('click', (event, d) => {
          selectedMint.value = {
            id: d.id,
            name: d.name || '',
            url: d.url || '',
            balance: d.balance,
            state: d.state,
            info: '',
            updated_at: new Date().toISOString(),
            next_update: new Date().toISOString(),
            n_errors: 0,
            n_mints: 0,
            n_melts: 0,
            sum_donations: 0
          };
          showSwapStats.value = true;
        });

      node.append('title')
        .text((d) => `Name: ${d.name || d.url}\nBalance: ${d.balance}`);

      const label = container.append('g')
        .attr('class', 'labels')
        .selectAll('text')
        .data(nodes)
        .enter().append('text')
        .attr('dx', 20)
        .attr('dy', '.45em')
        .text((d) => d.name || d.url || '')
        .attr('fill', '#fff')
        .style('font-weight', 'bold');

      function ticked() {
        link.attr('d', (d) => {
          const source = d.source as GraphNode;
          const target = d.target as GraphNode;
          const dx = target.x! - source.x!;
          const dy = target.y! - source.y!;
          const dr = Math.sqrt(dx * dx + dy * dy);
          return `M${source.x},${source.y} A${dr},${dr} 0 0,1 ${target.x},${target.y}`;
        });

        node
          .attr('cx', (d) => d.x!)
          .attr('cy', (d) => d.y!);

        label
          .attr('x', (d) => d.x!)
          .attr('y', (d) => d.y!);
      }
    };

    const drag = (simulation: d3.Simulation<GraphNode, GraphLink>) => {
      function dragstarted(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>, d: GraphNode) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
        // Stop zoom behavior when dragging nodes
        event.sourceEvent.stopPropagation();
      }

      function dragged(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>, d: GraphNode) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>, d: GraphNode) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }

      return d3.drag<SVGCircleElement, GraphNode>()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
    };

    const getStateColor = (state: string) => {
      switch (state) {
        case 'OK':
          return 'green';
        case 'WARN':
          return 'yellow';
        case 'ERROR':
          return 'red';
        case 'UNKNOWN':
        default:
          return 'grey';
      }
    };

    onMounted(() => {
      // Remove automatic loading
    });

    onBeforeUnmount(() => {
      if (simulation) {
        simulation.stop();
      }
    });

    return {
      svgRef,
      tooltipRef,
      loading,
      error,
      isLoaded,
      loadGraph,
      getStateColor,
      showSwapStats,
      selectedMint
    };
  },
});
</script>

<style scoped>
.mint-graph-container {
  position: relative;
  width: 100%;
  height: 600px;
  border-radius: 4px;
  overflow: hidden;
}

/* Add responsive styles */
@media (max-width: 600px) {
  .mint-graph-container {
    height: 400px; /* Reduce height on small screens */
  }

  .labels text {
    font-size: 10px; /* Smaller font on small screens */
  }

  .tooltip {
    font-size: 10px;
    max-width: 200px; /* Prevent tooltip from overflowing */
  }
}

.load-button-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1;
  background-color: rgba(0, 0, 0, 0.5);
  padding: 3rem;
  border-radius: 8px;
  transition: opacity 0.3s ease;
}

svg {
  width: 100%;
  height: 100%;
  display: block;
}

.nodes circle {
  cursor: pointer;
  stroke: #fff;
  stroke-width: 1.5px;
}

.links path {
  stroke-opacity: 0.6;
}

.labels text {
  pointer-events: none;
  font-size: 12px;
}

.tooltip {
  position: absolute;
  background-color: rgba(0, 0, 0, 0.7);
  color: #fff;
  padding: 5px;
  border-radius: 3px;
  pointer-events: none;
  font-size: 12px;
  z-index: 10;
}
</style>
