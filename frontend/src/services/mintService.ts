// src/services/mintService.ts

import api from './api';
import { MintRead, SwapEventRead, ChargeRequest, MintGraph, MintStats } from 'src/models/mint';

export const getMints = async (skip = 0, limit = 100): Promise<MintRead[]> => {
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

export const getMintStats = async (): Promise<MintStats> => {
  const response = await api.get<MintStats>('/stats/');
  console.log('API Response:', response.data);
  return response.data;
}

export async function getMintSwaps(mintId: number, skip = 0, limit = 10): Promise<SwapEventRead[]> {
  const response = await api.get(`/swaps/mint/${mintId}?skip=${skip}&limit=${limit}`);
  return response.data;
}

export async function getPaymentRequest(): Promise<string> {
  const response = await api.get<string>('/pr');
  return response.data;
}
