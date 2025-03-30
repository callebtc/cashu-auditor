<template>
  <div class="bar-chart-container">
    <div class="chart-wrapper">
      <div class="bars-container">
        <div v-for="(swap, index) in displaySwaps"
             :key="swap?.id || `placeholder-${index}`"
             class="bar"
             :class="{
               'success': swap?.state === 'OK',
               'failure': swap?.state === 'ERROR',
               'placeholder': !swap
             }"
             :style="{
               width: `${100 / displaySwaps.length}%`,
               left: `${(index / displaySwaps.length) * 100}%`
             }"
             @mouseover="swap && showTooltip($event, swap)"
             @mouseleave="hideTooltip">
        </div>
      </div>
      <div class="time-axis">
        <div v-for="(date, index) in timeTicks"
             :key="index"
             class="time-tick"
             :style="{ left: `${(index / (timeTicks.length - 1)) * 100}%` }">
          {{ formatTime(date) }}
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

      // Use the same time range logic as in displaySwaps
      const startTime = new Date(props.swaps[props.swaps.length - 1].created_at).getTime(); // Latest swap
      const endTime = new Date(props.swaps[0].created_at).getTime(); // Oldest swap

      const interval = (endTime - startTime) / 4; // 5 ticks (start, 3 middle, end)

      // Generate time ticks from newest to oldest to match bar positions
      return Array.from({ length: 5 }, (_, i) => new Date(startTime + (interval * i)));
    });

    const displaySwaps = computed(() => {
      if (props.swaps.length === 0) return Array(40).fill(null);

      // Create an array of 20 slots (or however many we want to show)
      const slots = Array(40).fill(null);
      const startTime = new Date(props.swaps[props.swaps.length - 1].created_at).getTime(); // Latest swap (the API returns in descending order)
      const endTime = new Date(props.swaps[0].created_at).getTime(); // Oldest swap
      const timeRange = endTime - startTime;

      if (timeRange === 0) {
        // If all swaps happened at the same time, just place the first one
        if (props.swaps.length > 0) {
          slots[0] = props.swaps[0];
        }
        return slots;
      }

      // Fill in the actual swaps
      props.swaps.forEach(swap => {
        const swapTime = new Date(swap.created_at).getTime();
        // Calculate index based on time position between newest and oldest
        // We reverse the calculation to match the visual orientation (oldest on right)
        const normalizedPosition = (swapTime - startTime) / timeRange;
        const index = Math.floor(normalizedPosition * (slots.length - 1));

        if (index >= 0 && index < slots.length) {
          slots[index] = swap;
        }
      });

      return slots;
    });

    const formatTime = (date: Date) => {
      const today = new Date();
      const isToday = date.toDateString() === today.toDateString();
      const isYesterday = new Date(today.setDate(today.getDate() - 1)).toDateString() === date.toDateString();

      let dateStr = '';
      if (isToday) {
        dateStr = 'Today';
      } else if (isYesterday) {
        dateStr = 'Yesterday';
      } else {
        dateStr = date.toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric'
        });
      }

      return `${dateStr} ${date.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      })}`;
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

      const today = new Date();
      const isToday = dateObj.toDateString() === today.toDateString();
      const isYesterday = new Date(today.setDate(today.getDate() - 1)).toDateString() === dateObj.toDateString();

      let formattedDate = '';
      if (isToday) {
        formattedDate = 'Today';
      } else if (isYesterday) {
        formattedDate = 'Yesterday';
      } else {
        formattedDate = dateObj.toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric'
        });
      }

      return `${formattedDate} ${dateObj.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      })}`;
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
      displaySwaps,
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
  margin-top: 16px;
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
  position: relative;
   gap: 1px;
}

.bar {
  height: 100%;
  transition: height 0.3s ease;
  border-radius: 2px;
  min-width: 2px;
  max-width: 8px;
  position: absolute;
  top: 0;
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

.bar.placeholder {
  background-color: transparent;
  border: 1px solid #444;
}

.bar.placeholder:hover {
  filter: none;
}
</style>
