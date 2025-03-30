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
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="text-negative q-pa-md">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue';

export default defineComponent({
  name: 'TokenInput',
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

    return {
      tokenValue,
      submitting,
      errorMessage,
      handleSubmit
    };
  }
});
</script>

<style scoped>
.rounded-borders {
  border-radius: 8px;
}
</style>
