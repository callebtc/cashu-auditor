<template>
  <div class="q-pa-md">
    <h1 class="text-h6">Lightning Auditor</h1>
    <p>
      Donate Ecash from any Cashu mint so it can be audited perpetually. This app sends random Lightning payments between mints. Forever. The sats go in a circle until all is lost to fees or rugs. If a mint fails to pay an invoice, it is marked with a scary red label.
    </p>
  </div>
  <StatsCard />
  <GlobalSwapBarChart :max-swaps="1000" />
  <MintList />
  <MintGraph />
  <SwapList />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import MintList from 'components/MintList.vue';
import SwapList from 'components/SwapList.vue';
import MintGraph from 'components/MintGraph.vue';
import StatsCard from 'components/StatsCard.vue';
import GlobalSwapBarChart from 'components/GlobalSwapBarChart.vue';

export default defineComponent({
  name: 'IndexPage',
  components: {
    MintList,
    SwapList,
    MintGraph,
    StatsCard,
    GlobalSwapBarChart,
  },
});
</script>

<style>
/* Add any page-specific styles here */
</style>
