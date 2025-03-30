<template>
  <div class="q-px-md">
    <q-card class="bg-dark text-white rounded-borders">
      <q-card-section>
        <MintSwapBarChart :swaps="swaps" :maxBars="200" />
      </q-card-section>
    </q-card>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { SwapEventRead } from 'src/models/mint';
import { getSwaps } from 'src/services/mintService';
import MintSwapBarChart from './MintSwapBarChart.vue';

export default defineComponent({
  name: 'GlobalSwapBarChart',
  components: {
    MintSwapBarChart
  },
  props: {
    maxSwaps: {
      type: Number,
      default: 200
    }
  },
  setup(props) {
    const swaps = ref<SwapEventRead[]>([]);
    const loading = ref(false);
    const error = ref('');
    let intervalId: number | undefined;

    const fetchSwaps = async () => {
      loading.value = true;
      error.value = '';

      try {
        // Fetch the specified number of swaps
        const fetchedSwaps = await getSwaps(0, props.maxSwaps);

        // Sort swaps by creation time (ascending) for bar chart
        swaps.value = fetchedSwaps.sort((a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
      } catch (err) {
        error.value = 'Error fetching swaps.';
        console.error(err);
      } finally {
        loading.value = false;
      }
    };

    onMounted(() => {
      fetchSwaps();
      // Refresh every 60 seconds
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
      error
    };
  }
});
</script>

<style scoped>
.rounded-borders {
  border-radius: 12px;
}
</style>
