'use client';


/* ─── Types ─────────────────────────────────────── */
interface RevisionNote {
  id: number;
  revision_id: number;
  user_id: number;
  note_content: string;
  created_at?: string;
}

interface MenuLocation {
  id: number;
  name: string;
  slug: string;
  description?: string;
  theme_supports?: string;
  created_at?: string;
  updated_at?: string;
}

interface LocationAssignment {
  id: number;
  menu_id: number;
  location_id: number;
  menu_name?: string;
  location_name?: string;
  created_at?: string;
}

interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}
