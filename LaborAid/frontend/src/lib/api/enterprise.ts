import { apiClient, TIMEOUT } from './client';

export interface EnterpriseCompany {
  id: string | null;
  name: string;
  credit_code: string | null;
  reg_status: string | null;
  legal_person: string | null;
  reg_capital: string | null;
  establish_time: string | null;
  address: string | null;
  business_scope: string | null;
  company_type: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  profile_url: string | null;
  source: string;
  belong_org?: string | null;
  insured_count?: string | null;
  person_scope?: string | null;
}

export interface EnterpriseRiskSummary {
  penalty_count: number;
  exception_count: number;
  shixin_count: number;
  zhixing_count: number;
  m_pledge_count: number;
  pledge_count: number;
  spot_check_count: number;
  has_liquidation: boolean;
  has_risk: boolean;
}

export interface EnterpriseRiskItems {
  penalties: Record<string, unknown>[];
  exceptions: Record<string, unknown>[];
  shixin_items: Record<string, unknown>[];
  zhixing_items: Record<string, unknown>[];
}

export interface EnterpriseScanResult {
  search_key: string;
  company: EnterpriseCompany;
  risk_summary: EnterpriseRiskSummary;
  risks: EnterpriseRiskItems;
  external_search_url: string | null;
  disclaimer: string;
}

export interface EnterpriseStatus {
  configured: boolean;
  provider: string;
  api_code: string;
  message: string;
}

export const enterpriseApi = {
  status: async (): Promise<EnterpriseStatus> => {
    const res = await apiClient.get('/enterprise/status', { timeout: TIMEOUT.short });
    return res.data;
  },

  scan: async (searchKey: string): Promise<EnterpriseScanResult> => {
    const res = await apiClient.get('/enterprise/scan', {
      params: { search_key: searchKey },
      timeout: TIMEOUT.medium,
    });
    return res.data;
  },
};
