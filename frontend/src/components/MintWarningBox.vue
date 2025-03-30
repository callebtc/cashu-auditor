<template>
  <div class="warning-container" v-if="hasWarnings">
    <div class="warning-content">
      <q-icon name="warning" size="24px" class="warning-icon" />
      <div class="warning-text-container">
        <div class="warning-header">
          <div class="warning-title">Mint Warning</div>
        </div>
        <div class="warning-messages">
          <div v-for="(message, index) in warningMessages" :key="index" class="warning-message">
            {{ message }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { MintRead, SwapEventRead } from 'src/models/mint';

export default defineComponent({
  name: 'MintWarningBox',
  props: {
    mint: {
      type: Object as () => MintRead,
      required: true
    },
    swaps: {
      type: Array as () => SwapEventRead[],
      required: true
    },
    couldFetchInfo: {
      type: Boolean,
      default: true
    },
    inactiveThresholdDays: {
      type: Number,
      default: 1
    }
  },
  setup(props) {
    const warningMessages = computed(() => {
      const messages: string[] = [];

      // Check if mint info could be fetched
      if (!props.couldFetchInfo) {
        messages.push("Could not reach mint. Mint might be offline.");
      }

      // Check mint state
      if (props.mint.state === 'WARN' || props.mint.state === 'ERROR') {
        messages.push(`The auditor determined the mint's state as ${props.mint.state === 'WARN' ? 'dangerous' : 'disfunctional'}.`);
      } else if (props.mint.state === 'UNKNOWN') {
        messages.push("The auditor was not able to determine whether this mint works.");
      }

      // Check last successful swap
      const successfulSwaps = props.swaps.filter(swap => swap.state === 'OK');
      if (successfulSwaps.length > 0) {
        const lastSuccessfulSwap = new Date(successfulSwaps[0].created_at);
        const now = new Date();
        const daysDifference = (now.getTime() - lastSuccessfulSwap.getTime()) / (1000 * 60 * 60 * 24);

        if (daysDifference > props.inactiveThresholdDays) {
          const days = Math.floor(daysDifference);
          messages.push(`This mint was not tested for ${days} ${days === 1 ? 'day' : 'days'}, it could be unreachable.`);
        }
      } else if (props.swaps.length > 0) {
        // If there are swaps but none are successful
        messages.push("No successful swaps recorded for this mint, it might be unreachable.");
      }

      return messages;
    });

    const hasWarnings = computed(() => warningMessages.value.length > 0);

    return {
      warningMessages,
      hasWarnings
    };
  }
});
</script>

<style scoped>
.warning-container {
  width: 100%;
  position: relative;
  border-radius: 8px;
  border: 1px solid #f18408;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  padding: 8px;
  text-align: left;
  font-size: 14px;
  color: #f18408;
  margin-bottom: 16px;
  margin-top: 8px;
}

.warning-content {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 12px;
}

.warning-icon {
  flex-shrink: 0;
  color: #f18408;
}

.warning-text-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 2px;
}

.warning-header {
  align-self: stretch;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.warning-title {
  position: relative;
  line-height: 16px;
  font-weight: 500;
}

.warning-messages {
  align-self: stretch;
}

.warning-message {
  align-self: stretch;
  position: relative;
  line-height: 16px;
  margin-bottom: 4px;
}

.warning-message:last-child {
  margin-bottom: 0;
}
</style>
