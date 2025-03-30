<template>
  <div class="bar-chart-container">
    <div class="chart-title text-subtitle1 q-mb-sm">Swap Success Rate Over Time</div>
    <div class="chart-wrapper">
      <div class="bars-container">
        <div v-for="swap in swaps"
             :key="swap.id"
             class="bar"
             :class="{ 'success': swap.state === 'OK', 'failure': swap.state === 'ERROR' }"
             :style="{ width: `${100 / swaps.length}%` }"
             @mouseover="showTooltip($event, swap)"
             @mouseleave="hideTooltip">
        </div>
      </div>
      <div class="time-axis">
        <div v-for="(swap, index) in timeTicks"
             :key="index"
             class="time-tick"
             :style="{ left: `${(index / (timeTicks.length - 1)) * 100}%` }">
          {{ formatTime(swap) }}
        </div>
      </div>
    </div>
    <div v-if="tooltip.show"
         class="tooltip"
         :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
      {{ tooltip.content }}
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed } from 'vue';
import { SwapEventRead } from 'src/models/mint';

export default defineComponent({
  name: 'MintSwapBarChart',
  props: {
    swaps: {
      type: Array as () => SwapEventRead[],
      required: true
    }
  },
  setup(props) {
    const tooltip = ref({
      show: false,
      x: 0,
      y: 0,
      content: ''
    });

    const timeTicks = computed(() => {
      if (props.swaps.length === 0) return [];
      const startTime = new Date(props.swaps[props.swaps.length - 1].created_at).getTime();
      const endTime = new Date(props.swaps[0].created_at).getTime();
      const interval = (endTime - startTime) / 4; // 5 ticks (start, 3 middle, end)
      return Array.from({ length: 5 }, (_, i) => new Date(startTime + (interval * i)));
    });

    const formatTime = (date: Date) => {
      return date.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    };

    const formatDate = (dateStr: string) => {
      const hasTimezone = /([Zz]|[+\-]\d{2}:\d{2})$/.test(dateStr);
      let utcDateStr = dateStr;

      if (!hasTimezone) {
        utcDateStr += 'Z';
      }

      const dateObj = new Date(utcDateStr);
      if (isNaN(dateObj.getTime())) {
        return 'Invalid Date';
      }

      return dateObj.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    };

    const showTooltip = (event: MouseEvent, swap: SwapEventRead) => {
      tooltip.value = {
        show: true,
        x: event.clientX + 10,
        y: event.clientY + 10,
        content: `${swap.state === 'OK' ? 'Success' : 'Failed'} - ${formatDate(swap.created_at)}`
      };
    };

    const hideTooltip = () => {
      tooltip.value.show = false;
    };

    return {
      tooltip,
      timeTicks,
      formatTime,
      formatDate,
      showTooltip,
      hideTooltip
    };
  }
});
</script>

<style scoped>
.bar-chart-container {
  background-color: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  margin: 16px;
  position: relative;
}

.chart-title {
  color: white;
  text-align: center;
}

.chart-wrapper {
  position: relative;
  height: 100px;
}

.bars-container {
  display: flex;
  align-items: flex-end;
  height: 80px;
  background-color: #2d2d2d;
  border-radius: 4px;
  padding: 4px;
  gap: 1px;
}

.bar {
  height: 100%;
  transition: height 0.3s ease;
  border-radius: 2px;
  min-width: 2px;
  max-width: 8px;
}

.bar.success {
  background-color: #4CAF50;
}

.bar.failure {
  background-color: #f44336;
}

.bar:hover {
  filter: brightness(1.2);
}

.time-axis {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 20px;
  display: flex;
  justify-content: space-between;
  padding: 0 4px;
}

.time-tick {
  position: absolute;
  transform: translateX(-50%);
  color: #888;
  font-size: 10px;
  white-space: nowrap;
}

.tooltip {
  position: fixed;
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
  white-space: nowrap;
}
</style>
