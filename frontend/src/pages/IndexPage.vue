<template>
  <div class="q-pa-md">
    <h1 class="text-h6">Warning</h1>
    <p>Hi there, unfortunately this tool is totally broken right now and I can't fix it right away. All the errors you're seeing aren't actual errors, so things look a lot worse than they should (a lot of scary red labels).</p>
    <h1 class="text-h6">Lightning Auditor</h1>
    <p>
      Donate ecash from any Cashu mint so it can be audited perpetually. This app sends random Lightning payments between mints. Forever. The sats go in a circle until all is lost to fees or rugs. If a mint fails to pay an invoice, it is marked with a scary red label.
    </p>
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
