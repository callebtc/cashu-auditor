<!-- src/components/MintList.vue -->

<template>



  <div>
    <!-- Token Input -->
    <div class="q-pa-md">
      <!-- header: Donate token -->
      <q-item-label class="text-h6 q-mb-md" color="white">Donate ecash</q-item-label>
      <q-input
        filled
        v-model="token"
        label="Enter Token"
        @keyup.enter="submitToken"
      >
        <template v-slot:append>
          <q-btn color="primary" @click="submitToken" ><q-spinner v-if="loading" size="15px" class="q-mr-sm" color="white" />Submit</q-btn>
        </template>
      </q-input>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="text-negative q-pa-md">
      {{ error }}
    </div>

    <!-- Mints Table -->
    <q-table
      title="Mints"
      :rows="mints"
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
          <q-icon :name="getStateIcon(props.row.state).name" :color="getStateIcon(props.row.state).color" />
        </td>
      </template>
      <template v-slot:body-cell-n_errors="props">
        <td class="text-left">
          <q-badge :color="props.row.n_errors > 0 && props.row.state == 'ERROR'? 'negative' : 'grey-7'" >{{ props.row.n_errors }}</q-badge>
        </td>
      </template>
      <template v-slot:body-cell-n_melts="props">
        <td class="text-left">
          <q-badge :color="props.row.n_melts > 0 && props.row.state == 'OK' ? 'positive' : 'grey-7'" text-color="dark">{{ props.row.n_melts }}</q-badge>
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
      { name: 'version', label: 'Version', field: 'info', sortable: true, align: 'left' },
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
        // monkeypatch version into info field
        mints.value.forEach(mint => {
          if (mint.info) { mint.info = getVersion(mint.info) };
        });
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

    const getStateIcon = (state: string) => {
      switch (state) {
        case 'OK':
          return { name: 'check_circle', color: 'positive' };
        case 'WARN':
          return { name: 'warning', color: 'warning' };
        case 'ERROR':
          return { name: 'cancel', color: 'negative' };
        case 'UNKNOWN':
        default:
          return { name: 'help', color: 'grey-7' };
      }
    };

    const getVersion = (info: string) => {
      try {
        const parsedInfo = JSON.parse(info);
        return parsedInfo.version;
      } catch (err) {
        return '';
      }
    };


    onMounted(() => {
      fetchMints();
      intervalId = window.setInterval(fetchMints, 60_000);
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
      getStateIcon,
      getVersion
    };
  },
});
</script>

<style scoped>
/* Add any component-specific styles here */
</style>
