'use client';


/* ─── Types ─────────────────────────────────────── */
interface FieldPermission {
  id: number;
  role_id: number;
  model_name: string;
  field_name: string;
  can_read: boolean;
  can_write: boolean;
  created_at?: string;
}

interface UserSession {
  id: number;
  user_id: number;
  access_token?: string;
  refresh_token?: string;
  device_info?: string;
  ip_address?: string;
  location?: string;
  is_active: boolean;
  last_activity?: string;
  expires_at?: string;
  created_at?: string;
}

interface EmailSubscription {
  id: number;
  user_id: number;
  subscribed: boolean;
  created_at?: string;
}

interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}
