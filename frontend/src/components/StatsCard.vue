<!-- src/components/StatsCard.vue -->

<template>
  <div class="q-pa-md">
    <q-card flat class="bg-dark text-white">
      <q-separator />

      <!-- Card Content: Statistic Cards arranged horizontally -->
      <q-card-section class="row items-start q-gutter-md">
        <!-- Total Balance -->
        <q-card class="stat-card">
          <q-card-section>
            <div class="text-subtitle1">Total Balance</div>
            <div class="text-h5">{{ formatNumber(stats.total_balance) }} sat</div>
          </q-card-section>
        </q-card>

        <!-- Total Swaps -->
        <q-card class="stat-card">
          <q-card-section>
            <div class="text-subtitle1">Total Swaps</div>
            <div class="text-h5">{{ formatNumber(stats.total_swaps) }}</div>
            <div class="text-caption">
              Last 24h: {{ formatNumber(stats.total_swaps_24h) }}
            </div>
          </q-card-section>
        </q-card>

        <!-- Total Amount Swapped -->
        <q-card class="stat-card">
          <q-card-section>
            <div class="text-subtitle1">Total Amount Swapped</div>
            <div class="text-h5">{{ formatNumber(stats.total_amount_swapped) }} sat</div>
            <div class="text-caption">
              Last 24h: {{ formatNumber(stats.total_amount_swapped_24h) }} sat
            </div>
          </q-card-section>
        </q-card>

        <!-- Average Swap Time -->
        <q-card class="stat-card">
          <q-card-section>
            <div class="text-subtitle1">Average Swap Time</div>
            <div class="text-h5">{{ formatTime(stats.average_swap_time) }}</div>
            <div class="text-caption">
              Last 24h: {{ formatTime(stats.average_swap_time_24h) }}
            </div>
          </q-card-section>
        </q-card>
      </q-card-section>

      <!-- Loading Indicator -->
      <q-linear-progress
        v-if="loading"
        indeterminate
        color="primary"
        class="q-mt-sm"
      />

      <!-- Error Message -->
      <div v-if="error" class="text-negative q-pa-md">
        {{ error }}
      </div>
    </q-card>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { getMintStats } from 'src/services/mintService';

interface ServiceStats {
  total_balance: number;
  total_swaps: number;
  total_swaps_24h: number;
  total_amount_swapped: number;
  total_amount_swapped_24h: number;
  average_swap_time: number; // in milliseconds
  average_swap_time_24h: number; // in milliseconds
}

export default defineComponent({
  name: 'StatsCard',
  setup() {
    const stats = ref<ServiceStats>({
      total_balance: 0,
      total_swaps: 0,
      total_swaps_24h: 0,
      total_amount_swapped: 0,
      total_amount_swapped_24h: 0,
      average_swap_time: 0,
      average_swap_time_24h: 0,
    });
    const loading = ref(false);
    const error = ref('');
    let intervalId: number | undefined;

    const fetchStats = async () => {
      loading.value = true;
      error.value = '';
      try {
        stats.value = await getMintStats();
      } catch (err) {
        error.value = 'Error fetching service statistics.';
        console.error(err);
      } finally {
        loading.value = false;
      }
    };

    const formatNumber = (num: number) => {
      return num.toLocaleString();
    };

    const formatTime = (milliseconds: number) => {
      if (milliseconds === 0) return 'N/A';
      const seconds = milliseconds / 1000;
      if (seconds < 60) {
        return `${seconds.toFixed(1)} s`;
      } else {
        const minutes = seconds / 60;
        return `${minutes.toFixed(1)} min`;
      }
    };

    onMounted(() => {
      fetchStats();
      // Refresh stats every 5 minutes
      intervalId = window.setInterval(fetchStats, 300_000);
    });

    onBeforeUnmount(() => {
      if (intervalId !== undefined) {
        clearInterval(intervalId);
      }
    });

    return {
      stats,
      loading,
      error,
      formatNumber,
      formatTime,
    };
  },
});
</script>

<style scoped>
.stat-card {
  flex: 1;
  min-width: 150px;
  background-color: #1e1e1e; /* Dark background for the card */
  color: white;
  min-height: 115px;
}
</style>
