<!-- src/components/SwapList.vue -->

<template>
  <div>
    <q-list bordered padding class="q-pa-md">
      <q-item-label header class="text-h6 q-mb-md">Recent Swaps</q-item-label>

      <div v-for="swap in swaps" :key="swap.id">
        <q-item clickable class="q-my-md">
          <q-item-section avatar>
            <q-icon
              :name="swap.state === 'OK' ? 'check_circle' : 'cancel'"
              :color="swap.state === 'OK' ? 'positive' : 'negative'"
            />
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
            <q-item-label v-if="swap.state === 'OK'" caption>
              <span class="text-bold">Fee:</span> {{ swap.fee }} sat
              <q-item-label v-if="swap.time_taken" caption>
                Payment took {{ swap.time_taken }} ms
              </q-item-label>
            </q-item-label>
          </q-item-section>
          <q-item-section side top>
            <q-item-label caption>{{ formatDate(swap.created_at) }}</q-item-label>
          </q-item-section>
        </q-item>
        <q-separator />
      </div>

      <!-- Load More Button -->
      <div class="q-pa-md" v-if="!allLoaded && !loading">
        <q-btn
          label="Load More Swaps"
          color="primary"
          @click="loadMoreSwaps"
          :disabled="loading"
          unelevated
        />
      </div>

      <!-- Loading Spinner -->
      <q-spinner v-if="loading" color="primary" size="50px" class="q-my-md" />

      <!-- Error Message -->
      <div v-if="error" class="text-negative q-pa-md">
        {{ error }}
      </div>

      <!-- No More Swaps Message -->
      <div v-if="allLoaded && swaps.length > 0" class="text-secondary q-pa-md">
        All swaps loaded.
      </div>

      <!-- No Swaps Found -->
      <div v-if="!loading && swaps.length === 0 && !error" class="text-secondary q-pa-md">
        No swaps found.
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
    const skip = ref(0);
    const limit = 10;
    const allLoaded = ref(false);

    let intervalId: number | undefined;

    // Fetch swaps with pagination
    const fetchSwaps = async (initial = false) => {
      if (loading.value || (allLoaded.value && !initial)) return;

      loading.value = true;
      error.value = '';

      try {
        const currentSkip = initial ? 0 : skip.value;
        const fetchedSwaps = await getSwaps(currentSkip, limit);

        if (initial) {
          swaps.value = fetchedSwaps;
          skip.value = limit;
          allLoaded.value = fetchedSwaps.length < limit;
        } else {
          swaps.value = [...swaps.value, ...fetchedSwaps];
          skip.value += limit;
          if (fetchedSwaps.length < limit) {
            allLoaded.value = true;
          }
        }

        // Sort swaps by created_at descending
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

    // Initial fetch
    const fetchInitialSwaps = async () => {
      await fetchSwaps(true);
    };

    // Load more swaps
    const loadMoreSwaps = async () => {
      await fetchSwaps();
    };

    const formatDate = (dateStr: string) => {
      return new Date(dateStr).toLocaleString();
    };

    onMounted(() => {
      fetchInitialSwaps();
      intervalId = window.setInterval(fetchInitialSwaps, 60_000); // Refresh every minute
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
      allLoaded,
      formatDate,
      loadMoreSwaps,
    };
  },
});
</script>

<style scoped>
.text-bold {
  font-weight: bold;
}
</style>
