import apiClient from './client';
import type { PlatformCategoryId } from '@/lib/channels';

export interface GlobalLink {
  id: string;
  title: string;
  description: string;
  url?: string;
  platform_key?: string;
  type: string;
}

export interface GuidanceStep {
  title: string;
  when?: string;
  action: 'internal' | 'external' | 'platform';
  tool_id?: string;
  hint?: string;
  url?: string;
  note?: string;
  platform_category?: PlatformCategoryId;
}

export interface CauseGuidance {
  summary: string;
  steps: GuidanceStep[];
}

export interface GuidanceData {
  global_links: GlobalLink[];
  cause_guidance: Record<string, CauseGuidance>;
  disclaimer: string;
}

export const guidanceApi = {
  get: () => apiClient.get<GuidanceData>('/guidance').then((r) => r.data),
};
