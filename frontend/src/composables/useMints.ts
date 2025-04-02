import { ref, readonly } from 'vue';
import { MintRead } from 'src/models/mint';
import { getMints } from 'src/services/mintService';

// Create a shared state that can be used across components
const mints = ref<MintRead[]>([]);
const loading = ref(false);
const error = ref('');

// Function to fetch mints data
const fetchMints = async () => {
  loading.value = true;
  error.value = '';
  try {
    const fetchedMints = await getMints(0, 100);
    // Process mints if needed (like version extraction)
    fetchedMints.forEach(mint => {
      if (mint.info) {
        try {
          const parsedInfo = JSON.parse(mint.info);
          mint.info = parsedInfo.version || mint.info;
        } catch (err) {
          // Keep original info if parsing fails
        }
      }
    });
    mints.value = fetchedMints;
  } catch (err) {
    console.error('Error fetching mints:', err);
    error.value = 'Error fetching mints.';
  } finally {
    loading.value = false;
  }
};

// Find a mint by URL
const findMintByUrl = (url: string): MintRead | undefined => {
  return mints.value.find(mint => mint.url === url);
};

// Expose the composable
export function useMints() {
  return {
    mints: readonly(mints),
    loading: readonly(loading),
    error,
    fetchMints,
    findMintByUrl
  };
}
