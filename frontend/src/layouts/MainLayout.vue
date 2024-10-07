<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated class="item-center">
      <q-toolbar class="bg-marginal-bg">

        <q-toolbar-title class="q-py-md q-mx-auto">
          Swap Auditor for Cashu mints
        </q-toolbar-title>

        <q-space />
        <theme-selector />

      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script lang="ts">
import { defineComponent } from 'vue';


export default defineComponent({
  name: 'MainLayout',

  components: {
  },

  setup () {

    return {
    }
  }
});
</script>
<style scoped>
.title-centered {
  text-align: center;
  max-width: 500px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
