// src/services/mintService.ts

import api from './api';
import { MintRead, SwapEventRead, ChargeRequest, MintGraph } from 'src/models/mint';

export const getMints = async (skip = 0, limit = 0): Promise<MintRead[]> => {
  const response = await api.get<MintRead[]>('/mints/', {
    params: { skip, limit },
  });
  console.log('API Response:', response.data);
  return response.data;
};

export const createMint = async (chargeRequest: ChargeRequest): Promise<MintRead> => {
  const response = await api.post<MintRead>('/mints/', chargeRequest);
  console.log('API Response:', response.data);
  return response.data;
};

export const getSwaps = async (skip = 0, limit = 10): Promise<SwapEventRead[]> => {
  const response = await api.get<SwapEventRead[]>('/swaps/', {
    params: { skip, limit },
  });
  console.log('API Response:', response.data);
  return response.data;
}

export const getMintGraph = async (): Promise<MintGraph> => {
  const response = await api.get<MintGraph>('/graph/');
  console.log('API Response:', response.data);
  return response.data;
}
