<!-- src/components/SwapList.vue -->

<template>
  <div>
    <q-list bordered padding class="q-pa-md">
      <q-item-label header class="text-h6 q-mb-md">Recent Swaps</q-item-label>

      <div v-for="swap in swaps" :key="swap.id">
        <q-item clickable class="q-my-md" @click="openMintStats(swap)">
          <q-item-section avatar>
            <q-icon
              :name="swap.state === 'OK' ? 'check_circle' : 'cancel'"
              :color="swap.state === 'OK' ? 'positive' : 'negative'"
            />
          </q-item-section>
          <q-item-section>
            <div class="row justify-between items-center">
              <div class="col-auto">
                <span class="text-bold">From:</span>
              </div>
              <div class="col-auto">
                <q-item-label caption>{{ formatDate(swap.created_at) }}</q-item-label>
              </div>
            </div>
            <q-item-label>
              {{ swap.from_url }}
              <q-btn
                flat
                round
                dense
                size="xs"
                icon="content_copy"
                class="copy-btn"
                @click.stop="copyToClipboard(swap.from_url, 'Source mint URL copied to clipboard')"
              >
                <q-tooltip>Copy URL</q-tooltip>
              </q-btn>
            </q-item-label>
            <q-item-label>
              <span class="text-bold">To:</span>
              {{ swap.to_url }}
              <q-btn
                flat
                round
                dense
                size="xs"
                icon="content_copy"
                class="copy-btn"
                @click.stop="copyToClipboard(swap.to_url, 'Destination mint URL copied to clipboard')"
              >
                <q-tooltip>Copy URL</q-tooltip>
              </q-btn>
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
            <q-item-label v-if="swap.state === 'ERROR' && swap.error" caption>
              <span class="text-bold" >Error:</span> {{ swap.error }}
            </q-item-label>
          </q-item-section>
        </q-item>
        <q-separator />
      </div>

      <div
        v-if="!allLoaded && !loadingMore && !loadingNewSwaps"
        class="q-pa-md flex justify-center"
      >
        <q-btn
          label="Load More Swaps"
          outline
          color="primary"
          :disabled="loadingMore"
          @click="loadMoreSwaps"
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

    <!-- Mint Swap Stats Dialog -->
    <MintSwapStats
      v-if="selectedMint"
      v-model="showSwapStats"
      :mint="selectedMint"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { SwapEventRead, MintRead } from 'src/models/mint';
import { getSwaps } from 'src/services/mintService';
import { copyToClipboard } from 'src/utils/clipboard';
import MintSwapStats from './MintSwapStats.vue';
import { useMints } from 'src/composables/useMints';

export default defineComponent({
  name: 'SwapList',
  components: {
    MintSwapStats
  },
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

    // Variables for MintSwapStats dialog
    const showSwapStats = ref(false);
    const selectedMint = ref<MintRead | null>(null);

    // Access the mints from the composable
    const { mints, fetchMints, findMintByUrl } = useMints();

    // Set to track existing swap IDs for duplicate prevention
    const swapIds = ref<Set<number>>(new Set());

    // Interval ID for periodic fetch
    let intervalId: number | undefined;

    /**
     * Opens MintSwapStats dialog for the source mint of a swap
     * @param swap - The swap to show stats for
     */
    const openMintStats = (swap: SwapEventRead) => {
      // Ensure mints are loaded
      if (mints.value.length === 0) {
        fetchMints();
      }

      // Try to find the mint by URL
      const mint = findMintByUrl(swap.from_url);

      if (mint) {
        // Use the full mint object with all properties
        selectedMint.value = mint;
      } else {
        // Fallback to creating a basic mint object if not found
        selectedMint.value = {
          id: swap.from_id,
          url: swap.from_url,
          name: '', // Default empty name
          balance: 0, // Default balance
          updated_at: swap.created_at,
          state: swap.state,
          n_errors: 0,
          n_mints: 0,
          n_melts: 0
        };
      }

      showSwapStats.value = true;
    };

    /**
     * Formats a date string into a readable format.
     * @param dateStr - The date string to format.
     * @returns A localized date string.
     */
     const formatDate = (dateStr: string) => {
      // Check if the dateStr already ends with 'Z' or contains timezone info
      const hasTimezone = /([Zz]|[+-]\d{2}:\d{2})$/.test(dateStr);
      let utcDateStr = dateStr;

      if (!hasTimezone) {
        // Append 'Z' to indicate UTC if no timezone is present
        utcDateStr += 'Z';
      }

      const dateObj = new Date(utcDateStr);
      if (isNaN(dateObj.getTime())) {
        console.error(`Invalid date string: ${dateStr}`);
        return 'Invalid Date';
      }

      // Define options for time formatting
      const timeOptions: Intl.DateTimeFormatOptions = {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      };

      // Define options for date formatting
      const dateOptions: Intl.DateTimeFormatOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      };

      // Format time and date separately
      const time = dateObj.toLocaleTimeString(undefined, timeOptions);
      const date = dateObj.toLocaleDateString(undefined, dateOptions);

      // Return in the format: <time>, <date>
      return `${time}, ${date}`;
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
      // First, ensure we have mints loaded
      await fetchMints();
      // Then fetch initial swaps
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
      copyToClipboard,
      // Add new properties for MintSwapStats
      selectedMint,
      showSwapStats,
      openMintStats
    };
  },
});
</script>

<style scoped>
.text-bold {
  font-weight: bold;
}

.copy-btn {
  margin-left: 4px;
  opacity: 0.7;
}

.copy-btn:hover {
  opacity: 1;
}
</style>
