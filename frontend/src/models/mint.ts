// src/models/mint.ts

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
