// src/services/api.ts

import axios from 'axios';

const api = axios.create({
  baseURL: process.env.VUE_BASE_URL || 'https://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
