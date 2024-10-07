<template>
  <q-select
    v-model="selectedTheme"
    :options="themes"
    label="Select Theme"
    @update:model-value="changeTheme"
  />
</template>

<script lang="ts">
import { defineComponent, ref, getCurrentInstance } from 'vue';

export default defineComponent({
  name: 'ThemeSelector',
  setup() {
    const themes = [
      'classic',
      'bitcoin',
      'freedom',
      'salvador',
      'mint',
      'autumn',
      'flamingo',
      'monochrome',
      'cyber',
    ];
    const selectedTheme = ref(localStorage.getItem('theme') || 'classic');

    const { proxy } = getCurrentInstance();

    const changeTheme = (themeName: string) => {
      proxy.$setTheme(themeName);
      localStorage.setItem('theme', themeName);
    };

    return {
      themes,
      selectedTheme,
      changeTheme,
    };
  },
});
</script>
