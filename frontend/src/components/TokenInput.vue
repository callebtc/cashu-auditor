<!-- src/components/TokenInput.vue -->

<template>
  <div>
    <div class="q-pa-md">
      <!-- header: Donate token -->
      <q-item-label class="text-h6 q-mb-md" color="white">Donate Ecash</q-item-label>
      <q-input
        filled
        v-model="tokenValue"
        label="Enter Token"
        @keyup.enter="handleSubmit"
        class="rounded-borders"
      >
        <template v-slot:append>
          <q-btn color="primary" @click="handleSubmit">
            <q-spinner v-if="submitting" size="15px" class="q-mr-sm" color="white" />Submit
          </q-btn>
        </template>
      </q-input>
      <div class="q-mt-md row justify-end">
        <q-btn color="primary" v-if="!paymentRequestString" @click="createPaymentRequest" :loading="loadingPaymentRequest">Payment Request</q-btn>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="text-negative q-pa-md">
      {{ errorMessage }}
    </div>

    <!-- Payment Request QR Code -->
    <div v-if="paymentRequestString" class="q-pa-md q-mt-md">
      <div class="row text-center items-center justify-center">
        <qrcode :value="paymentRequestString" :options="{ width: 200 }" class="q-mb-md"></qrcode>
      </div>
      <div class="row text-center items-center justify-center">
          <q-input v-model="paymentRequestString" class="q-mb-md" style="font-family: monospace; font-size: 12px; max-width: 400px;" readonly >
            <template v-slot:append>
              <q-icon name="content_copy" color="grey" size="xs" @click="copyToClipboard(paymentRequestString)"></q-icon>
            </template>
          </q-input>
        </div>
        <div class="row text-center items-center justify-center q-mb-md">
          <q-btn color="primary" outline @click="hidePaymentRequest">Hide</q-btn>
        </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue';
import QRCode from '@chenfengyuan/vue-qrcode';
import { getPaymentRequest } from 'src/services/mintService';
import { copyToClipboard } from 'src/utils/clipboard';

export default defineComponent({
  name: 'TokenInput',
  components: {
    qrcode: QRCode
  },
  props: {
    token: {
      type: String,
      default: ''
    },
    submittingToken: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: ''
    }
  },
  emits: ['update:token', 'submit'],
  setup(props, { emit }) {
    const tokenValue = ref(props.token);
    const submitting = ref(props.submittingToken);
    const errorMessage = ref(props.error);
    const paymentRequestString = ref('');
    const loadingPaymentRequest = ref(false);

    // Watch for prop changes and update local refs
    watch(() => props.token, (newValue) => {
      tokenValue.value = newValue;
    });

    watch(() => props.submittingToken, (newValue) => {
      submitting.value = newValue;
    });

    watch(() => props.error, (newValue) => {
      errorMessage.value = newValue;
    });

    // Watch for local changes and emit updates
    watch(tokenValue, (newValue) => {
      emit('update:token', newValue);
    });

    const handleSubmit = () => {
      emit('submit');
    };

    const createPaymentRequest = async () => {
      loadingPaymentRequest.value = true;
      errorMessage.value = '';

      try {
        const response = await getPaymentRequest();
        paymentRequestString.value = response.pr
      } catch (error) {
        console.error('Error fetching payment request:', error);
        errorMessage.value = 'Failed to generate payment request. Please try again.';
      } finally {
        loadingPaymentRequest.value = false;
      }
    };

    const hidePaymentRequest = () => {
      paymentRequestString.value = '';
    };

    return {
      tokenValue,
      submitting,
      errorMessage,
      handleSubmit,
      createPaymentRequest,
      paymentRequestString,
      loadingPaymentRequest,
      hidePaymentRequest,
      copyToClipboard
    };
  }
});
</script>

<style scoped>
.rounded-borders {
  border-radius: 8px;
}
</style>
