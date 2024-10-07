<!-- src/components/MintList.vue -->

<template>



  <div>
    <!-- Token Input -->
    <div class="q-pa-md">
      <q-card>
      <q-input
        filled
        v-model="token"
        label="Enter Token"
        @keyup.enter="submitToken"
      >
        <template v-slot:append>
          <q-btn label="Submit" color="primary" @click="submitToken" />
          <q-spinner v-if="loading" size="50px" class="q-my-md" color="primary" />
        </template>
      </q-input>
      </q-card>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="text-negative q-pa-md">
      {{ error }}
    </div>

    <!-- Mints Table -->
    <q-table
      title="Mints"
      :rows="mints"
      :grid="$q.screen.xs"
      :columns="columns"
      row-key="id"
      :loading="loading"
      :hide-bottom="mints.length > 0"
      :rows-per-page-options="[0]"
    >
      <!-- Custom Cell for Date Formatting -->
      <template v-slot:body-cell-updated_at="props">
        <td class="text-left">
          {{ formatDate(props.row.updated_at) }}
        </td>
      </template>
      <template v-slot:body-cell-next_update="props">
        <td class="text-left">
          {{ formatDate(props.row.next_update) }}
        </td>
      </template>
      <template v-slot:body-cell-state="props">
        <td class="text-left">
          <q-icon :name="props.row.state === 'OK' ? 'check_circle' : 'cancel'" :color="props.row.state === 'OK' ? 'positive' : 'negative'"/>
        </td>
      </template>
    </q-table>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { MintRead } from 'src/models/mint';
import { getMints, createMint } from 'src/services/mintService';

export default defineComponent({
  name: 'MintList',
  setup() {
    const token = ref('');
    const mints = ref<MintRead[]>([]);
    const loading = ref(false);
    const error = ref('');

    const columns = [
      // { name: 'id', label: 'ID', field: 'id', sortable: true, align: 'left' },
      { name: 'url', label: 'URL', field: 'url', sortable: true, align: 'left' },
      // { name: 'info', label: 'Info', field: 'info', sortable: true },
      { name: 'name', label: 'Name', field: 'name', sortable: true, align: 'left' },
      { name: 'balance', label: 'Balance (sat)', field: 'balance', sortable: true, align: 'left' },
      { name: 'sum_donations', label: 'Total donated (sat)', field: 'sum_donations', sortable: true, align: 'left' },
      { name: 'updated_at', label: 'Updated At', field: 'updated_at', sortable: true, align: 'left' },
      // { name: 'next_update', label: 'Next Update', field: 'next_update', sortable: true, align: 'left' },
      { name: 'state', label: 'State', field: 'state', sortable: true, align: 'left' },
      { name: 'n_errors', label: 'Errors', field: 'n_errors', sortable: true, align: 'left' },
      { name: 'n_mints', label: 'Mints', field: 'n_mints', sortable: true, align: 'left' },
      { name: 'n_melts', label: 'Melts', field: 'n_melts', sortable: true, align: 'left' },
    ];

    let intervalId: number | undefined;

    const fetchMints = async () => {
      loading.value = true;
      error.value = '';
      try {
        mints.value = await getMints(0, 0);
      } catch (err) {
        error.value = 'Error fetching mints.';
        console.error(err);
      } finally {
        loading.value = false;
      }
    };

    const submitToken = async () => {
      if (!token.value) return;
      loading.value = true;
      error.value = '';
      try {
        await createMint({ token: token.value });
        token.value = '';
        await fetchMints();
      } catch (err) {
        error.value = 'Error submitting token.';
        console.error(err);
      } finally {
        loading.value = false;
      }
    };

    const formatDate = (dateStr: string) => {
      return new Date(dateStr).toLocaleString();
    };

    onMounted(() => {
      fetchMints();
      intervalId = window.setInterval(fetchMints, 60_000); // Fetch every 10 seconds
    });

    onBeforeUnmount(() => {
      if (intervalId !== undefined) {
        clearInterval(intervalId);
      }
    });

    return {
      token,
      mints,
      columns,
      loading,
      error,
      submitToken,
      formatDate,
    };
  },
});
</script>

<style scoped>
/* Add any component-specific styles here */
</style>
