<template>
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
