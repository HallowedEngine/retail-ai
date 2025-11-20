import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Base64 encode for basic auth
const authHeader = () => {
  const credentials = Buffer.from('admin:retailai2025').toString('base64');
  return `Basic ${credentials}`;
};

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': authHeader(),
  },
});

// Types
export interface Product {
  id: number;
  sku: string;
  name: string;
  category?: string;
  barcode_gtin?: string;
  shelf_life_days?: number;
  image_url?: string;
}

export interface Invoice {
  id: number;
  created_at: string;
  line_count?: number;
}

export interface InvoiceLine {
  id: number;
  product_id?: number;
  name_raw: string;
  qty: number;
  unit: string;
  unit_price: number;
}

export interface ExpiryAlert {
  id: number;
  product_id: number;
  batch_id: number;
  expiry_date: string;
  days_left: number;
  severity: 'red' | 'yellow';
  created_at: string;
  status?: string;
  snooze_until?: string;
}

export interface DashboardSummary {
  expiry_count: number;
  low_stock_count: number;
  recent_invoices: Invoice[];
}

// API Methods
export const dashboardApi = {
  getSummary: async (storeId = 1, days = 7): Promise<DashboardSummary> => {
    const { data } = await api.get(`/dashboard/summary?store_id=${storeId}&days=${days}`);
    return data;
  },
};

export const invoiceApi = {
  upload: async (file: File, storeId = 1, supplierId = 1) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post(`/upload_invoice?store_id=${storeId}&supplier_id=${supplierId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  getDetails: async (invoiceId: number) => {
    const { data } = await api.get(`/invoice/${invoiceId}`);
    return data;
  },

  getRecent: async (limit = 20): Promise<Invoice[]> => {
    const { data } = await api.get(`/invoices/recent?limit=${limit}`);
    return data;
  },

  exportCSV: async (invoiceId: number) => {
    const response = await api.get(`/invoice/${invoiceId}/export.csv`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const productApi = {
  list: async (query?: string, limit = 30): Promise<Product[]> => {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    params.append('limit', limit.toString());
    const { data } = await api.get(`/products?${params}`);
    return data;
  },

  create: async (product: Partial<Product>) => {
    const { data } = await api.post('/products', product);
    return data;
  },

  bulkCreate: async (products: Partial<Product>[]) => {
    const { data } = await api.post('/products/bulk', products);
    return data;
  },
};

export const alertApi = {
  getExpiry: async (storeId = 1, days = 30): Promise<ExpiryAlert[]> => {
    const { data } = await api.get(`/alerts/expiry/full?store_id=${storeId}&days=${days}`);
    return data;
  },

  acknowledge: async (alertId: number, note?: string) => {
    const { data } = await api.post(`/alerts/${alertId}/ack`, { note });
    return data;
  },

  snooze: async (alertId: number, days = 1, note?: string) => {
    const { data } = await api.post(`/alerts/${alertId}/snooze`, { days, note });
    return data;
  },
};
