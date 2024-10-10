<template>
  <q-card class="bg-dark">
  <q-card-section class="bg-dark text-light">
    <h2 class="text-h6">Mint Graph</h2>
  </q-card-section>
  <div class="mint-graph-container">
    <svg ref="svgRef"></svg>
    <q-spinner v-if="loading" color="primary" size="50px" class="q-my-md" />
    <div v-if="error" class="text-negative q-pa-md">
      {{ error }}
    </div>
    <div ref="tooltip" class="tooltip" style="opacity: 0;"></div>
  </div>
</q-card>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { MintGraph } from 'src/models/mint';
import { getMintGraph } from 'src/services/mintService';
import * as d3 from 'd3';

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
  setup() {
    const svgRef = ref<SVGSVGElement | null>(null);
    const tooltipRef = ref<HTMLDivElement | null>(null); // Reference for the tooltip
    const mintGraph = ref<MintGraph | null>(null);
    const loading = ref(false);
    const error = ref('');
    let simulation: d3.Simulation<GraphNode, GraphLink> | null = null;

    const fetchMintGraph = async () => {
      loading.value = true;
      error.value = '';
      try {
        mintGraph.value = await getMintGraph();
        renderGraph();
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
        .attr('viewBox', `-250 -200 800 550`)
        .attr('preserveAspectRatio', 'xMidYMid meet');

      // Define arrowhead markers
      svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 25) // Adjust based on link distance
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('xoverflow', 'visible')
        .append('svg:path')
        .attr('d', 'M 0,-5 L 10,0 L 0,5') // Arrow shape
        .attr('fill', '#aaa')
        .style('stroke', 'none');

      const tooltip = d3.select(tooltipRef.value);

      simulation = d3.forceSimulation<GraphNode, GraphLink>(nodes)
        // .force('link', d3.forceLink<GraphNode, GraphLink>(links).id((d) => d.id.toString()).distance(300))
          .force('link', d3.forceLink<GraphNode, GraphLink>(links)
          .id((d) => d.id.toString())
          .distance(250)
          .strength((d) => Math.sqrt(d.count) / 100)
        )
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('x', d3.forceX(width / 2).strength(0.01))
        .force('y', d3.forceY(height / 2).strength(0.05))
        .on('tick', ticked);

      const link = svg.append('g')
        .attr('class', 'links')
        .selectAll('path')
        .data(links)
        .enter().append('path')
        .attr('stroke-width', (d) => Math.sqrt(d.count))
        .attr('stroke', (d) => d.state === 'OK' ? '#7b7' : '#a66')
        .attr('stroke-opacity', 0.5)
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

      const node = svg.append('g')
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
        });

      node.append('title')
        .text((d) => `Name: ${d.name || d.url}\nBalance: ${d.balance}`);

      const label = svg.append('g')
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

    let intervalId: number | undefined;

    onMounted(() => {
      fetchMintGraph();
      // intervalId = window.setInterval(fetchMintGraph, 60_000);
    });

    onBeforeUnmount(() => {
      if (simulation) {
        simulation.stop();
      }
      if (intervalId !== undefined) {
        clearInterval(intervalId);
      }
    });

    return {
      svgRef,
      tooltipRef, // Return tooltipRef here
      loading,
      error,
      getStateColor
    };
  },
});
</script>

<style scoped>
.mint-graph-container {
  position: relative;
  width: 100%;
  height: 600px;
}

svg {
  border: 1px solid #ccc;
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
  z-index: 10; /* Ensure tooltip is on top */
}
</style>
