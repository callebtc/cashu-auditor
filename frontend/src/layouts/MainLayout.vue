<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar class="bg-marginal-bg relative-position">

        <!-- Centered Title -->
        <q-toolbar-title class="title-centered">
          Round Robin Cashu
        </q-toolbar-title>

        <!-- Right-aligned Elements -->
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
      // Expose any necessary data or methods
    };
  }
});
</script>

<style scoped>
.relative-position {
  position: relative; /* Establishes a containing block for absolutely positioned children */
}

.title-centered {
  position: absolute;        /* Positions the title absolutely within the toolbar */
  left: 50%;                 /* Moves the title 50% from the left */
  transform: translateX(-50%); /* Centers the title by translating it left by 50% of its own width */
  text-align: center;        /* Centers the text within the title element */
  max-width: 500px;          /* Optional: Limits the maximum width of the title */
  white-space: nowrap;       /* Prevents the title from wrapping to the next line */
  overflow: hidden;          /* Hides any overflowed content */
  text-overflow: ellipsis;   /* Adds ellipsis (...) for overflowed text */
}
</style>
