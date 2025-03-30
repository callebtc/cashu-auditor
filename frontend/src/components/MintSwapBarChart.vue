<template>
  <div class="bar-chart-container">
    <div class="chart-wrapper">
      <div class="bars-container">
        <div v-for="(bucket, index) in displayBuckets"
             :key="`bucket-${index}`"
             class="bar"
             :class="{
               'placeholder': bucket.count === 0
             }"
             :style="{
               width: `${100 / displayBuckets.length}%`,
               left: `${(index / displayBuckets.length) * 100}%`,
               backgroundColor: bucket.count > 0 ? getSuccessColor(bucket.successRate) : 'transparent'
             }"
             @mouseover="showBucketTooltip($event, bucket)"
             @mouseleave="hideTooltip">
        </div>
      </div>
      <div class="time-axis">
        <div v-for="(date, index) in timeTicks"
             :key="index"
             class="time-tick"
             :style="{
               left: `${(index / (timeTicks.length - 1)) * 100}%`,
               display: index === timeTicks.length - 1 ? 'none' : 'block'
             }">
          {{ formatTime(date) }}
        </div>
      </div>
    </div>
    <div v-if="tooltip.show"
         class="tooltip"
         :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
      <div v-html="tooltip.content"></div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted } from 'vue';
import { SwapEventRead } from 'src/models/mint';

interface SwapBucket {
  swaps: SwapEventRead[];
  count: number;
  successCount: number;
  successRate: number;
  startTime: Date;
  endTime: Date;
}

export default defineComponent({
  name: 'MintSwapBarChart',
  props: {
    swaps: {
      type: Array as () => SwapEventRead[],
      required: true
    },
    maxBars: {
      type: Number,
      default: 40
    }
  },
  setup(props) {
    const tooltip = ref({
      show: false,
      x: 0,
      y: 0,
      content: ''
    });

    const screenWidth = ref(window.innerWidth);
    const isSmallScreen = computed(() => screenWidth.value < 768);

    const barsCount = computed(() => {
      return isSmallScreen.value ? Math.min(20, props.maxBars) : props.maxBars;
    });

    onMounted(() => {
      const handleResize = () => {
        screenWidth.value = window.innerWidth;
      };

      window.addEventListener('resize', handleResize);
      return () => {
        window.removeEventListener('resize', handleResize);
      };
    });

    const timeTicks = computed(() => {
      if (props.swaps.length === 0) return [];

      // Use the same time range logic as in displayBuckets
      const startTime = new Date(props.swaps[0].created_at).getTime(); // Oldest swap
      const endTime = new Date(props.swaps[props.swaps.length - 1].created_at).getTime(); // Latest swap

      const interval = (startTime - endTime) / 3; // 4 ticks (now, 2 middle, end)

      // Generate time ticks from oldest to newest to match bar positions
      return Array.from({ length: 4 }, (_, i) => new Date(endTime + (interval * i)));
    });

    const displayBuckets = computed(() => {
      if (props.swaps.length === 0) {
        return Array(barsCount.value).fill({
          swaps: [],
          count: 0,
          successCount: 0,
          successRate: 0,
          startTime: new Date(),
          endTime: new Date()
        });
      }

      // Sort swaps by creation time (ascending)
      const sortedSwaps = [...props.swaps].sort((a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );

      // Create buckets based on time
      const endTime = new Date(sortedSwaps[sortedSwaps.length - 1].created_at).getTime(); // Latest swap
      const startTime = new Date(sortedSwaps[0].created_at).getTime(); // Oldest swap
      const timeRange = endTime - startTime;

      const buckets: SwapBucket[] = Array(barsCount.value).fill(null).map(() => ({
        swaps: [],
        count: 0,
        successCount: 0,
        successRate: 0,
        startTime: new Date(),
        endTime: new Date()
      }));

      if (timeRange === 0) {
        // If all swaps happened at the same time, place them in the first bucket
        buckets[0].swaps = [...sortedSwaps];
        buckets[0].count = sortedSwaps.length;
        buckets[0].successCount = sortedSwaps.filter(swap => swap.state === 'OK').length;
        buckets[0].successRate = buckets[0].count > 0 ? buckets[0].successCount / buckets[0].count : 0;
        buckets[0].startTime = new Date(startTime);
        buckets[0].endTime = new Date(endTime);
        return buckets;
      }

      // Calculate bucket time ranges
      const bucketTimeSpan = timeRange / barsCount.value;

      for (let i = 0; i < barsCount.value; i++) {
        // Reverse the order: newest (latest) on the left, oldest on the right
        const reversedIndex = barsCount.value - 1 - i;
        const bucketStartTime = startTime + (reversedIndex * bucketTimeSpan);
        const bucketEndTime = startTime + ((reversedIndex + 1) * bucketTimeSpan);

        buckets[i].startTime = new Date(bucketStartTime);
        buckets[i].endTime = new Date(bucketEndTime);
      }

      // Assign swaps to buckets
      sortedSwaps.forEach(swap => {
        const swapTime = new Date(swap.created_at).getTime();

        // Find which bucket this swap belongs to (reversing order so newest is on left)
        const normalizedPosition = (swapTime - startTime) / timeRange; // 0 = oldest, 1 = newest
        const reversedPosition = 1 - normalizedPosition; // 0 = newest, 1 = oldest
        const bucketIndex = Math.min(
          Math.floor(reversedPosition * barsCount.value),
          barsCount.value - 1
        );

        if (bucketIndex >= 0) {
          buckets[bucketIndex].swaps.push(swap);
          buckets[bucketIndex].count++;
          if (swap.state === 'OK') {
            buckets[bucketIndex].successCount++;
          }
        }
      });

      // Calculate success rates for each bucket
      buckets.forEach(bucket => {
        bucket.successRate = bucket.count > 0 ? bucket.successCount / bucket.count : 0;
      });

      return buckets;
    });

    const getSuccessColor = (successRate: number) => {
      // Convert success rate to a color from red (0%) to orange (50%) to green (100%)
      if (successRate === 1) return '#4CAF50'; // Pure green for 100%
      if (successRate === 0) return '#f44336'; // Pure red for 0%

      if (successRate < 0.5) {
        // Red to orange gradient (0% to 50%)
        const r = 244;
        const g = Math.floor(67 + (successRate * 2 * (165 - 67)));
        const b = 54;
        return `rgb(${r}, ${g}, ${b})`;
      } else {
        // Orange to green gradient (50% to 100%)
        const r = Math.floor(244 - ((successRate - 0.5) * 2 * (244 - 76)));
        const g = Math.floor(165 + ((successRate - 0.5) * 2 * (175 - 165)));
        const b = Math.floor(54 - ((successRate - 0.5) * 2 * (54 - 50)));
        return `rgb(${r}, ${g}, ${b})`;
      }
    };

    const formatTime = (date: Date) => {
      // Special case for the most recent time (leftmost tick)
      if (props.swaps.length > 0) {
        const latestSwapTime = new Date(props.swaps[props.swaps.length - 1].created_at).getTime();
        if (Math.abs(date.getTime() - latestSwapTime) < 1000) { // Within 1 second
          return "Now";
        }
      }

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

    const showBucketTooltip = (event: MouseEvent, bucket: SwapBucket) => {
      if (bucket.count === 0) {
        hideTooltip();
        return;
      }

      const successRate = Math.round(bucket.successRate * 100);
      let timeRange = '';

      if (bucket.startTime && bucket.endTime) {
        timeRange = `${formatDate(bucket.startTime.toISOString())} - ${formatDate(bucket.endTime.toISOString())}`;
      }

      tooltip.value = {
        show: true,
        x: event.clientX + 10,
        y: event.clientY + 10,
        content: `
          <div><b>Swaps:</b> ${bucket.count}</div>
          <div><b>Success rate:</b> ${successRate}% (${bucket.successCount}/${bucket.count})</div>
          <div><b>Time range:</b> ${timeRange}</div>
        `
      };
    };

    const hideTooltip = () => {
      tooltip.value.show = false;
    };

    return {
      tooltip,
      timeTicks,
      displayBuckets,
      barsCount,
      formatTime,
      formatDate,
      showBucketTooltip,
      hideTooltip,
      getSuccessColor
    };
  }
});
</script>

<style scoped>
.bar-chart-container {
  background-color: #1e1e1e;
  border-radius: 8px;
  padding-bottom: 6px;
  padding-top: 20px;
  padding-left: 20px;
  padding-right: 20px;
  position: relative;
}

.chart-title {
  color: white;
  text-align: center;
}

.chart-wrapper {
  position: relative;
  height: 65px;
}

.bars-container {
  display: flex;
  align-items: flex-end;
  height: 40px;
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
