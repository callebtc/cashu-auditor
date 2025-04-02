// src/models/mint.ts

export interface PaymentRequestResponse {
  pr: string;
}

export interface MintRead {
  id: number;
  url: string;
  info?: string;
  name?: string;
  balance: number;
  sum_donations?: number;
  updated_at: string;
  next_update?: string;
  state: string;
  n_errors: number;
  n_mints: number;
  n_melts: number;
}

export interface SwapEventRead {
  id: number;
  from_id: number;
  to_id: number;
  from_url: string;
  to_url: string
  amount: number;
  fee: number;
  created_at: string;
  time_taken: number;
  state: string;
  error: string;
}

export interface ChargeRequest {
  token: string;
}

export interface MintGraphEdge {
  from_id: number;
  to_id: number;
  count: number;
  total_amount: number;
  total_fee: number;
  last_swap: string;
  state: string;
}

export interface MintGraph {
  nodes: MintRead[];
  edges: MintGraphEdge[];
}

export interface MintStats {
  total_balance: number;
  total_swaps: number;
  total_swaps_24h: number;
  total_amount_swapped: number;
  total_amount_swapped_24h: number;
  average_swap_time: number;
  average_swap_time_24h: number;
}
