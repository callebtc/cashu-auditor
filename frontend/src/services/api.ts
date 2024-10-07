// src/services/api.ts

import axios from 'axios';

const api = axios.create({
  // baseURL: process.env.VITE_API_BASE_URL || 'https://api.audit.8333.space',
  baseURL: 'https://api.audit.8333.space',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
