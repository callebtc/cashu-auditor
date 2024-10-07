<!-- src/components/SwapList.vue -->

<template>
  <div>
    <q-list bordered padding class="q-pa-md">
      <q-item-label header class="text-h6 q-mb-md">Recent Swaps</q-item-label>
      <div v-for="swap in swaps" :key="swap.id" >
      <q-item clickable class="q-my-md">
        <q-item-section avatar>
          <q-icon :name="swap.state === 'OK' ? 'check_circle' : 'cancel'" :color="swap.state === 'OK' ? 'positive' : 'negative'"/>
        </q-item-section>
        <q-item-section>
          <q-item-label>
            <span class="text-bold">From:</span> {{ swap.from_url }}
          </q-item-label>
          <q-item-label>
            <span class="text-bold">To:</span> {{ swap.to_url }}
          </q-item-label>
          <q-item-label>
            <span class="text-bold">Amount:</span> {{ swap.amount }} sat
          </q-item-label>
          <q-item-label v-if="swap.state=='OK'" caption>
            <span class="text-bold">Fee:</span> {{ swap.fee }} sat
            <q-item-label v-if="swap.time_taken" caption>Payment took {{ swap.time_taken }} ms</q-item-label>
          </q-item-label>
        </q-item-section>
        <q-item-section side top>
          <q-item-label caption>{{ formatDate(swap.created_at) }}</q-item-label>
        </q-item-section>
      </q-item>
      <q-separator />
    </div>
      <q-spinner v-if="loading" color="primary" size="50px" class="q-my-md" />
      <div v-if="error" class="text-negative q-pa-md">
        {{ error }}
      </div>
    </q-list>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { SwapEventRead } from 'src/models/mint';
import { getSwaps } from 'src/services/mintService';

export default defineComponent({
  name: 'SwapList',
  setup() {
    const swaps = ref<SwapEventRead[]>([]);
    const loading = ref(false);
    const error = ref('');

    let intervalId: number | undefined;

    const fetchSwaps = async () => {
      loading.value = true;
      error.value = '';
      try {
        swaps.value = await getSwaps(0, 10);
        // sort by created_at
        swaps.value.sort((a, b) => {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
      } catch (err) {
        error.value = 'Error fetching swaps.';
        console.error(err);
      } finally {
        loading.value = false;
      }
    };

    const formatDate = (dateStr: string) => {
      return new Date(dateStr).toLocaleString();
    };

    onMounted(() => {
      fetchSwaps();
      intervalId = window.setInterval(fetchSwaps, 60_000);
    });

    onBeforeUnmount(() => {
      if (intervalId !== undefined) {
        clearInterval(intervalId);
      }
    });

    return {
      swaps,
      loading,
      error,
      formatDate,
    };
  },
});
</script>

<style scoped>
.text-bold {
  font-weight: bold;
}
</style>
