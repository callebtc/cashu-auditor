<!-- src/components/MintList.vue -->

<template>
  <div>
    <!-- Token Input -->
    <TokenInput
      v-model:token="token"
      :submittingToken="submittingToken"
      :error="error"
      @submit="submitToken"
    />

    <!-- Mints Table -->
    <q-table
      title="Mints"
      :rows="mints"
      :columns="columns"
      row-key="id"
      :loading="loading"
      :hide-bottom="mints.length > 0"
      :rows-per-page-options="[0]"
      @row-click="onRowClick"
    >
      <!-- Add subtitle -->
      <template v-slot:top-right>
        <div class="text-caption text-grey-7">Click on a mint to get more information</div>
      </template>

      <!-- Add URL cell template for monospace font -->
      <template v-slot:body-cell-url="props">
        <td class="text-left" style="font-family: monospace;">
          {{ props.row.url }}
          <q-btn
            flat
            round
            dense
            size="xs"
            icon="content_copy"
            @click.stop="copyToClipboard(props.row.url)"
            class="copy-btn"
          >
            <q-tooltip>Copy URL</q-tooltip>
          </q-btn>
        </td>
      </template>

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

    <!-- Mint Swap Stats Dialog -->
    <MintSwapStats
      v-if="selectedMint"
      v-model="showSwapStats"
      :mint="selectedMint"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { MintRead } from 'src/models/mint';
import { getMints, createMint } from 'src/services/mintService';
import MintSwapStats from './MintSwapStats.vue';
import TokenInput from './TokenInput.vue';
import { copyToClipboard } from 'src/utils/clipboard';

export default defineComponent({
  name: 'MintList',
  components: {
    MintSwapStats,
    TokenInput
  },
  setup() {
    const token = ref('');
    const mints = ref<MintRead[]>([]);
    const loading = ref(false);
    const submittingToken = ref(false);
    const error = ref('');
    const showSwapStats = ref(false);
    const selectedMint = ref<MintRead | null>(null);

    const columns = [
      // { name: 'id', label: 'ID', field: 'id', sortable: true, align: 'left' },
      { name: 'url', label: 'URL', field: 'url', sortable: true, align: 'left' as const },
      // { name: 'info', label: 'Info', field: 'info', sortable: true },
      { name: 'name', label: 'Name', field: 'name', sortable: true, align: 'left' as const },
      { name: 'version', label: 'Version', field: 'info', sortable: true, align: 'left' as const },
      { name: 'balance', label: 'Balance (sat)', field: 'balance', sortable: true, align: 'left' as const },
      { name: 'sum_donations', label: 'Total donated (sat)', field: 'sum_donations', sortable: true, align: 'left' as const },
      { name: 'updated_at', label: 'Updated At', field: 'updated_at', sortable: true, align: 'left' as const },
      // { name: 'next_update', label: 'Next Update', field: 'next_update', sortable: true, align: 'left' },
      { name: 'state', label: 'State', field: 'state', sortable: true, align: 'left' as const },
      { name: 'n_errors', label: 'Errors', field: 'n_errors', sortable: true, align: 'left' as const },
      { name: 'n_mints', label: 'Mints', field: 'n_mints', sortable: true, align: 'left' as const },
      { name: 'n_melts', label: 'Melts', field: 'n_melts', sortable: true, align: 'left' as const },
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
      submittingToken.value = true;
      error.value = '';
      try {
        await createMint({ token: token.value });
        token.value = '';
        await fetchMints();
      } catch (err) {
        error.value = 'Error submitting token.';
        console.error(err);
      } finally {
        submittingToken.value = false;
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

    const onRowClick = (evt: any, row: MintRead) => {
      selectedMint.value = row;
      showSwapStats.value = true;
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
      submittingToken,
      error,
      submitToken,
      formatDate,
      getStateIcon,
      getVersion,
      showSwapStats,
      selectedMint,
      onRowClick,
      copyToClipboard
    };
  },
});
</script>

<style scoped>
/* Add any component-specific styles here */
.copy-btn {
  margin-left: 4px;
  opacity: 0.7;
}

.copy-btn:hover {
  opacity: 1;
}
</style>
