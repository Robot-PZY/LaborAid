from pydantic import BaseModel, Field


class EnterpriseCompanyOut(BaseModel):
    id: str | None = None
    name: str
    credit_code: str | None = None
    reg_status: str | None = None
    legal_person: str | None = None
    reg_capital: str | None = None
    establish_time: str | None = None
    address: str | None = None
    business_scope: str | None = None
    company_type: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    profile_url: str | None = None
    source: str = "qichacha"
    belong_org: str | None = None
    insured_count: str | None = None
    person_scope: str | None = None


class EnterpriseRiskSummaryOut(BaseModel):
    penalty_count: int = 0
    exception_count: int = 0
    shixin_count: int = 0
    zhixing_count: int = 0
    m_pledge_count: int = 0
    pledge_count: int = 0
    spot_check_count: int = 0
    has_liquidation: bool = False
    has_risk: bool = False


class EnterpriseRiskItemsOut(BaseModel):
    penalties: list[dict] = Field(default_factory=list)
    exceptions: list[dict] = Field(default_factory=list)
    shixin_items: list[dict] = Field(default_factory=list)
    zhixing_items: list[dict] = Field(default_factory=list)


class EnterpriseScanOut(BaseModel):
    search_key: str
    company: EnterpriseCompanyOut
    risk_summary: EnterpriseRiskSummaryOut
    risks: EnterpriseRiskItemsOut
    external_search_url: str | None = None
    disclaimer: str = "数据来源于企查查公开信息，仅供参考，请以市场监管部门及司法机关官方登记为准。"


class EnterpriseStatusOut(BaseModel):
    configured: bool
    provider: str = "qichacha"
    api_code: str = "736"
    message: str
