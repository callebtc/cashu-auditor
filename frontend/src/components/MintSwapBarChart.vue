<template>
  <div class="bar-chart-container">
    <div class="chart-title text-subtitle1 q-mb-sm">Swap Success Rate Over Time</div>
    <div class="chart-wrapper">
      <div v-for="swap in swaps"
           :key="swap.id"
           class="bar"
           :class="{ 'success': swap.state === 'OK', 'failure': swap.state === 'ERROR' }"
           :style="{ width: `${100 / swaps.length}%` }"
           :title="`${swap.state === 'OK' ? 'Success' : 'Failed'} - ${formatDate(swap.created_at)}`">
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { SwapEventRead } from 'src/models/mint';

export default defineComponent({
  name: 'MintSwapBarChart',
  props: {
    swaps: {
      type: Array as () => SwapEventRead[],
      required: true
    }
  },
  setup() {
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

    return {
      formatDate
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
}

.chart-title {
  color: white;
  text-align: center;
}

.chart-wrapper {
  display: flex;
  align-items: flex-end;
  height: 100px;
  background-color: #2d2d2d;
  border-radius: 4px;
  padding: 4px;
  gap: 2px;
}

.bar {
  height: 100%;
  transition: height 0.3s ease;
  border-radius: 2px;
  min-width: 4px;
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
</style>
