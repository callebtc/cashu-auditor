<template>
  <q-dialog v-model="show">
    <q-card class="bg-dark q-pa-sm text-white rounded-borders" :style="$q.screen.gt.sm ? { 'min-width': '600px' } : null">
      <q-card-actions align="left">
          <q-icon name="close" class="cursor-pointer text-white" v-close-popup/>
      </q-card-actions>
      <q-card-section class="row justify-center q-pb-md">
        <div class="text-h4">{{ mint.name || mint.url }}</div>
      </q-card-section>

      <q-card-section class="row justify-center q-pb-lg">
      <q-avatar size="75px" class="q-mb-lg">
        <q-img
          spinner-color="white"
          spinner-size="xs"
          :src="mintIconUrl"
          alt="Mint Icon"
          style="height: 75px; max-width: 75px; font-size: 12px"
        />
        </q-avatar>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <div class="row q-col-gutter-md q-pl-md">
          <!-- Success Rate Card -->
          <q-card class="col-6 stat-card">
            <q-card-section>
              <div class="text-subtitle1">Success Rate</div>
              <div class="text-h5">{{ successRate }}%</div>
              <div class="text-caption">
                {{ successfulSwaps }} of {{ swaps.length }} swaps
              </div>
            </q-card-section>
          </q-card>

          <!-- Average Time Card -->
          <q-card class="col-6 stat-card">
            <q-card-section>
              <div class="text-subtitle1">Average Time</div>
              <div class="text-h5">{{ formatTime(averageTime) }}</div>
              <div class="text-caption">
                For successful swaps
              </div>
            </q-card-section>
          </q-card>
        </div>
      </q-card-section>

      <q-card-section>
        <div class="text-h6 q-mb-md">Recent Swaps</div>
        <q-list bordered separator class="scroll" style="max-height: 400px" ref="swapList">
          <q-item v-for="swap in swaps" :key="swap.id" class="q-py-md">
            <q-item-section>
              <q-item-label>
                <span class="text-bold">To:</span> <span style="font-family: monospace;">{{ swap.to_url }}</span>
              </q-item-label>
              <q-item-label>
                <span class="text-bold">Amount:</span> {{ swap.amount }} sat
              </q-item-label>
              <q-item-label>
                <span class="text-bold">Time:</span> {{ formatDate(swap.created_at) }}
              </q-item-label>
              <q-item-label v-if="swap.state === 'OK'" caption>
                <span class="text-bold">Fee:</span> {{ swap.fee }} sat
                <q-item-label v-if="swap.time_taken" caption>
                  Payment took {{ swap.time_taken }} ms
                </q-item-label>
              </q-item-label>
              <q-item-label v-if="swap.state === 'ERROR' && swap.error" caption>
                <span class="text-bold">Error:</span> {{ swap.error }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-icon
                :name="swap.state === 'OK' ? 'check_circle' : 'cancel'"
                :color="swap.state === 'OK' ? 'positive' : 'negative'"
              />
            </q-item-section>
          </q-item>
          <q-item  class="q-pa-md">
            <q-item-section class="q-flex justify-center">
              <q-item-label class="text-center">
                <q-btn
                  label="Load More Swaps"
                  outline
                  color="primary"
                  @click="loadMoreSwaps"
                  :disabled="loadingMore"
                  :loading="loadingMore"
                />
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>



        <!-- No More Swaps Message -->
        <div v-if="allLoaded && swaps.length > 0" class="text-secondary q-pa-md">
          All swaps loaded.
        </div>

        <!-- No Swaps Found -->
        <div v-if="!loadingInitial && swaps.length === 0" class="text-secondary q-pa-md">
          No swaps found.
        </div>
      </q-card-section>

    </q-card>
  </q-dialog>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted, watch, nextTick } from 'vue';
import { MintRead, SwapEventRead } from 'src/models/mint';
import { getMintSwaps } from 'src/services/mintService';

export default defineComponent({
  name: 'MintSwapStats',
  props: {
    modelValue: {
      type: Boolean,
      required: true
    },
    mint: {
      type: Object as () => MintRead,
      required: true
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const swaps = ref<SwapEventRead[]>([]);
    const loadingInitial = ref(false);
    const loadingMore = ref(false);
    const skip = ref(0);
    const limit = 10;
    const allLoaded = ref(false);
    const swapList = ref<HTMLElement | null>(null);
    const mintIconUrl = ref<string | undefined>(undefined);

    const show = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    });

    // Add this watch effect after the show computed property
    watch(show, (newValue) => {
      if (newValue) {
        // Reset pagination
        skip.value = 0;
        allLoaded.value = false;
        // Reload data
        fetchSwaps('initial');
        getMintIcon(props.mint);
      }
    });

    const successfulSwaps = computed(() => {
      return swaps.value.filter(swap => swap.state === 'OK').length;
    });

    const successRate = computed(() => {
      if (swaps.value.length === 0) return 0;
      return Math.round((successfulSwaps.value / swaps.value.length) * 100);
    });

    const averageTime = computed(() => {
      const successfulSwapsWithTime = swaps.value.filter(swap =>
        swap.state === 'OK' && swap.time_taken
      );
      if (successfulSwapsWithTime.length === 0) return 0;
      const totalTime = successfulSwapsWithTime.reduce((sum, swap) =>
        sum + (swap.time_taken || 0), 0
      );
      return totalTime / successfulSwapsWithTime.length;
    });

    const fetchSwaps = async (type: 'initial' | 'more') => {
      if (type === 'initial') {
        loadingInitial.value = true;
      } else {
        loadingMore.value = true;
      }

      try {
        const fetchedSwaps = await getMintSwaps(props.mint.id, skip.value, limit);

        if (type === 'initial') {
          swaps.value = fetchedSwaps;
        } else {
          swaps.value = [...swaps.value, ...fetchedSwaps];
        }

        skip.value += limit;
        allLoaded.value = fetchedSwaps.length < limit;
      } catch (err) {
        console.error('Error fetching swaps:', err);
      } finally {
        if (type === 'initial') {
          loadingInitial.value = false;
        } else {
          loadingMore.value = false;
        }
      }
    };

    const loadMoreSwaps = async () => {
      if (allLoaded.value || loadingMore.value) return;

      // Store current scroll position
      const scrollPosition = swapList.value?.scrollTop || 0;

      await fetchSwaps('more');

      // After the DOM updates, restore scroll position
      nextTick(() => {
        if (swapList.value) {
          swapList.value.scrollTop = scrollPosition;
        }
      });
    };

    const formatTime = (milliseconds: number) => {
      if (milliseconds === 0) return 'N/A';
      const seconds = milliseconds / 1000;
      if (seconds < 10) {
        return `${milliseconds.toFixed(0)} ms`;
      } else {
        return `${seconds.toFixed(2)} s`;
      }
    };

    /**
     * Formats a date string into a readable format.
     * @param dateStr - The date string to format.
     * @returns A localized date string.
     */
     const formatDate = (dateStr: string) => {
      // Check if the dateStr already ends with 'Z' or contains timezone info
      const hasTimezone = /([Zz]|[+\-]\d{2}:\d{2})$/.test(dateStr);
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

    const getMintName = (mintId: number) => {
      // This should be replaced with actual mint name lookup
      return `Mint ${mintId}`;
    };

    const getMintIcon = async (mint: MintRead) => {
      try {
        const mintInfo = await fetch(mint.url + '/v1/info');
        const info = await mintInfo.json();
        mintIconUrl.value = info.icon_url;
      } catch (error) {
        console.error('Error fetching mint icon:', error);
        mintIconUrl.value = undefined;
      }
    };

    onMounted(() => {
      fetchSwaps('initial');
      getMintIcon(props.mint);
    });

    return {
      swapList,
      show,
      swaps,
      loadingInitial,
      loadingMore,
      allLoaded,
      successRate,
      successfulSwaps,
      averageTime,
      formatTime,
      getMintName,
      loadMoreSwaps,
      formatDate,
      mintIconUrl
    };
  }
});
</script>

<style scoped>
.stat-card {
  background-color: #1e1e1e;
  color: white;
  min-height: 100px;
  border-radius: 8px;
}

.rounded-borders {
  border-radius: 12px;
}

.scroll {
  overflow-y: auto;
}
</style>
