<template>
      <div class="text-center q-pa-md q-ma-lg q-card bg-dark text-light" style="font-family: 'Roboto', sans-serif; font-size: 1rem; border: 0px solid #ccc; max-width: 700px; margin: 20px auto 0px auto;">
      Round Robin Auditor: Donate ecash from any Cashu mint so it can be audited perpetually. This app forever sends random Lightning payments between mints. The sats go in an infinite circle (minus fees). If a mint fails to pay an invoice, it is marked with scary red label.
    </div>
  <MintList />
  <MintGraph />
  <SwapList />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import MintList from 'components/MintList.vue';
import SwapList from 'components/SwapList.vue';
import MintGraph from 'components/MintGraph.vue';

export default defineComponent({
  name: 'IndexPage',
  components: {
    MintList,
    SwapList,
    MintGraph,
  },
});
</script>

<style>
/* Add any page-specific styles here */
</style>
