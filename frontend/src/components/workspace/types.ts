export type WorkspaceType = "enterprise" | "consulting_agency";

export interface WorkspaceBranding {
  organization_id: number;
  workspace_type: WorkspaceType;
  display_name: string;
  logo_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  footer_text?: string | null;
}

export interface WorkspaceSummary {
  id: number;
  name: string;
  workspace_type: WorkspaceType;
  role: string;
  branding: WorkspaceBranding;
}

export interface PortfolioItem {
  assessment_id: number;
  company_name: string;
  business_unit?: string | null;
  status?: string | null;
  workflow_status?: string | null;
  approval_status?: string | null;
  investment_decision_status?: string | null;
  overall_score?: number | null;
  recommended_first_pilot?: string | null;
  locked_for_delivery?: boolean | number | null;
}

export interface EngagementItem {
  client_id: number;
  name: string;
  industry?: string | null;
  business_unit?: string | null;
  engagement_status?: string | null;
  assigned_consultant_user_id?: number | null;
  consultant_notes?: string | null;
  fee_estimate?: Record<string, unknown> | null;
  has_proposal?: boolean;
  has_sow?: boolean;
}

export interface ProposalSowPayload {
  proposal_package?: Record<string, unknown> | null;
  sow_package?: Record<string, unknown> | null;
  fee_estimate?: Record<string, unknown> | null;
  complete?: boolean;
}
