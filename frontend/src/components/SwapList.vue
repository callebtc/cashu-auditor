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
            <!-- error message -->
            <q-item-label v-if="swap.state === 'ERROR' && swap.error.length > 0" caption>
              <span class="text-bold" >Error:</span> {{ swap.error }}
            </q-item-label>
          </q-item-section>
          <q-item-section side top>
            <q-item-label caption>{{ formatDate(swap.created_at) }}</q-item-label>
          </q-item-section>
        </q-item>
        <q-separator />
      </div>

      <div
        class="q-pa-md flex justify-center"
        v-if="!allLoaded && !loadingMore && !loadingNewSwaps"
      >
        <q-btn
          label="Load More Swaps"
          outline
          color="primary"
          @click="loadMoreSwaps"
          :disabled="loadingMore"
        />
      </div>

      <!-- Loading More Spinner -->
      <q-spinner v-if="loadingMore" color="primary" size="50px" class="q-my-md" />

      <!-- Loading New Swaps Spinner -->
      <div v-if="loadingNewSwaps" class="q-pa-md">
        <q-spinner color="primary" size="30px" /> Loading new swaps...
      </div>

      <!-- Error Message -->
      <div v-if="error" class="text-negative q-pa-md">
        {{ error }}
      </div>

      <!-- No More Swaps Message -->
      <div v-if="allLoaded && swaps.length > 0" class="text-secondary q-pa-md">
        All swaps loaded.
      </div>

      <!-- No Swaps Found -->
      <div v-if="!loadingInitial && swaps.length === 0 && !error" class="text-secondary q-pa-md">
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
    // Reactive state variables
    const swaps = ref<SwapEventRead[]>([]);
    const loadingInitial = ref(false);    // Loading initial swaps
    const loadingMore = ref(false);       // Loading more swaps
    const loadingNewSwaps = ref(false);   // Loading new swaps
    const error = ref('');
    const skip = ref(0);
    const limit = 10;
    const allLoaded = ref(false);

    // Set to track existing swap IDs for duplicate prevention
    const swapIds = ref<Set<number>>(new Set());

    // Interval ID for periodic fetch
    let intervalId: number | undefined;

    /**
     * Formats a date string into a readable format.
     * @param dateStr - The date string to format.
     * @returns A localized date string.
     */
    const formatDate = (dateStr: string) => {
      return new Date(dateStr).toLocaleString();
    };

    /**
     * Fetches swaps from the API.
     * @param type - The type of fetch: 'initial', 'more', or 'new'.
     */
    const fetchSwaps = async (type: 'initial' | 'more' | 'new') => {
      // Determine the appropriate loading state
      if (type === 'initial') {
        loadingInitial.value = true;
      } else if (type === 'more') {
        loadingMore.value = true;
      } else if (type === 'new') {
        loadingNewSwaps.value = true;
      }

      error.value = '';

      try {
        if (type === 'initial') {
          // Fetch the first batch of swaps
          const fetchedSwaps = await getSwaps(0, limit);
          swaps.value = fetchedSwaps;
          swapIds.value = new Set(fetchedSwaps.map(swap => swap.id));
          skip.value = limit;
          allLoaded.value = fetchedSwaps.length < limit;
        } else if (type === 'more') {
          // Fetch the next batch based on current skip
          const fetchedSwaps = await getSwaps(skip.value, limit);
          // Append only new swaps
          const newSwaps = fetchedSwaps.filter(swap => !swapIds.value.has(swap.id));
          newSwaps.forEach(swap => swapIds.value.add(swap.id));
          swaps.value = [...swaps.value, ...newSwaps];
          skip.value += limit;
          if (fetchedSwaps.length < limit) {
            allLoaded.value = true;
          }
        } else if (type === 'new') {
          // Fetch the latest swaps (skip=0)
          const fetchedSwaps = await getSwaps(0, limit);
          // Prepend only new swaps
          const newSwaps = fetchedSwaps.filter(swap => !swapIds.value.has(swap.id));
          if (newSwaps.length > 0) {
            newSwaps.forEach(swap => swapIds.value.add(swap.id));
            swaps.value = [...newSwaps, ...swaps.value];
          }
        }

        // Sort swaps by created_at descendingly
        swaps.value.sort((a, b) => {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
      } catch (err) {
        error.value = 'Error fetching swaps.';
        console.error(err);
      } finally {
        // Reset loading states
        if (type === 'initial') {
          loadingInitial.value = false;
        } else if (type === 'more') {
          loadingMore.value = false;
        } else if (type === 'new') {
          loadingNewSwaps.value = false;
        }
      }
    };

    /**
     * Loads more swaps when "Load More" is clicked.
     */
    const loadMoreSwaps = async () => {
      if (allLoaded.value || loadingMore.value) return;
      await fetchSwaps('more');
    };

    /**
     * Periodically fetches new swaps to prepend to the list.
     */
    const fetchNewSwaps = async () => {
      await fetchSwaps('new');
    };

    /**
     * Initializes the component by fetching initial swaps and setting up the interval.
     */
    const initialize = async () => {
      await fetchSwaps('initial');
      // Set up interval to fetch new swaps every minute
      intervalId = window.setInterval(fetchNewSwaps, 60_000);
    };

    /**
     * Cleans up the interval when the component is unmounted.
     */
    onBeforeUnmount(() => {
      if (intervalId !== undefined) {
        clearInterval(intervalId);
      }
    });

    // Fetch initial swaps on component mount
    onMounted(() => {
      initialize();
    });

    return {
      swaps,
      loadingInitial,
      loadingMore,
      loadingNewSwaps,
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
