"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  ArrowRight, Plus, FileText, CheckCircle, TrendingUp, 
  BarChart3, Brain, Shield, Calendar, Download, Edit3, Save, 
  UploadCloud, Sparkles, RefreshCw, Trash2, AlertTriangle, LogOut,
  Coins
} from "lucide-react";
import WorkspaceSelector from "../components/workspace/WorkspaceSelector";
import EnterprisePortfolio from "../components/workspace/EnterprisePortfolio";
import AgencyEngagements from "../components/workspace/AgencyEngagements";
import ProposalSowEditor from "../components/workspace/ProposalSowEditor";
import ReviewApprovalPanel from "../components/workspace/ReviewApprovalPanel";
import MemberAccessPanel, {
  type WorkspaceMember,
} from "../components/workspace/MemberAccessPanel";
import type {
  EngagementItem,
  PortfolioItem,
  ProposalSowPayload,
  WorkspaceSummary,
} from "../components/workspace/types";
import { 
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, 
  ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Bar 
} from "recharts";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

type AssessmentStatus = "intake" | "uploading" | "processing" | "completed" | "failed";

interface ExtractedSignal {
  id?: number;
  assessment_id?: number;
  source_file: string;
  signal_type: string;
  description: string;
  confidence: number;
}

interface Bottleneck {
  id?: number;
  assessment_id?: number;
  department: string;
  process_name: string;
  bottleneck_description: string;
  ai_potential: string;
}

interface UseCase {
  id?: number;
  assessment_id?: number;
  department: string;
  use_case_name: string;
  description: string;
  value: string;
  complexity: string;
  risk: string;
  priority: string;
  evidence?: string | null;
  confidence: number;
}

interface Risk {
  id?: number;
  assessment_id?: number;
  risk_name: string;
  severity: string;
  recommendation: string;
  is_control_met: number;
}

interface RoadmapItem {
  id?: number;
  assessment_id?: number;
  phase: string;
  action_item: string;
  expected_impact: string;
  confidence: number;
}

interface ClientWorkspace {
  id: number;
  name: string;
  industry: string | null;
  company_size: string | null;
  cloud_preference: string | null;
  compliance_requirements: string[];
  created_at: string;
  updated_at: string;
}

interface Assessment {
  id: number;
  client_id: number | null;
  company_name: string;
  industry: string | null;
  company_size: string | null;
  departments: string[];
  current_tools: string[];
  cloud_preference: string | null;
  compliance_requirements: string[];
  main_business_goals: string | null;
  pain_points: string[];
  ai_goals: string[];
  overall_score: number;
  automation_potential: number;
  confidence_score: number;
  status: AssessmentStatus;
  risk_level: string;
  recommended_first_pilot: string | null;
  why_recommended_pilot: string | null;
  expected_pilot_impact: string | null;
  data_readiness: number;
  data_justification: string | null;
  process_readiness: number;
  process_justification: string | null;
  integration_readiness: number;
  integration_justification: string | null;
  governance_readiness: number;
  governance_justification: string | null;
  security_readiness: number;
  security_justification: string | null;
  team_readiness: number;
  team_justification: string | null;
  business_alignment: number;
  alignment_justification: string | null;
  business_summary: string | null;
  client_summary: string | null;
  reviewer_notes: string | null;
  approval_status: string | null;
  organization_id?: number | null;
  business_unit?: string | null;
  workflow_status?: string | null;
  locked_for_delivery?: number | boolean | null;
  readiness_interpretation: string | null;
  scoring_method?: string | null;
  scoring_rubric_version?: string | null;
  dimension_score_details?: Record<string, {
    justification?: string;
    evidence_refs?: string[];
    missing_information?: string[];
    estimate_flags?: string[];
    reviewer_status?: string;
    score?: number;
  }> | null;
  analysis_mode?: string | null;
  model_provider?: string | null;
  model_run_status?: string | null;
  insufficient_evidence?: number | null;
  automation_potential_basis?: string | null;
  prioritization_rubric_version?: string | null;
  financial_model_version?: string | null;
  investment_decision_status?: string | null;
  investment_decision_explanation?: string | null;
  recommended_opportunity_id?: number | null;
  pilot_plan?: Record<string, unknown> | null;
  investment_package?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  bottlenecks: Bottleneck[];
  use_cases: UseCase[];
  risks: Risk[];
  roadmap_items: RoadmapItem[];
  extracted_signals: ExtractedSignal[];
  client: ClientWorkspace | null;
}

interface InvestmentOpportunity {
  id?: number;
  use_case_id?: number | null;
  name?: string;
  use_case_name?: string;
  description?: string | null;
  department?: string | null;
  ranking?: number | null;
  weighted_priority_score?: number | null;
  ranking_explanation?: string | null;
  recommendation_status?: string | null;
  confidence_class?: string | null;
  is_blocked?: boolean;
  hard_blockers?: Array<{ code?: string; description?: string }>;
  missing_information?: string[];
  criterion_scores?: Record<string, { score?: number; weight?: number; basis?: string }>;
  feasibility?: {
    proposed_approach?: string;
    approach_rationale?: string;
    prerequisites?: string[];
    major_risks?: string[];
    score?: number;
  };
  financial_inputs?: Record<string, unknown>;
  financial_evaluation?: {
    evaluation_complete?: boolean;
    incomplete_message?: string | null;
    illustrative?: boolean;
    currency?: string;
    scenarios?: Record<string, {
      roi_percentage?: number | null;
      payback_months?: number | null;
      net_annual_savings?: number | null;
      implementation_investment?: number | null;
      gross_annual_savings?: number | null;
      current_baseline_annual_cost?: number | null;
    }>;
    sensitivity?: Array<{
      parameter?: string;
      delta_pct?: number;
      resulting_roi_pct?: number | null;
    }>;
  };
  pilot_selected?: boolean;
}

interface InvestmentPackage {
  opportunities?: InvestmentOpportunity[];
  pilot_recommendation?: {
    opportunity_name?: string;
    selection_rationale?: string;
    estimated_investment_label?: string;
    time_to_value_label?: string;
    success_metrics?: Array<Record<string, string>>;
    stages?: Array<Record<string, unknown>>;
    missing_information?: string[];
  } | null;
  decision_summary?: {
    status?: string | null;
    explanation?: string | null;
    missing_evidence?: string[];
  };
  prioritization_rubric_version?: string | null;
  financial_model_version?: string | null;
  review_events?: Array<Record<string, unknown>>;
}

interface AuthTokenResponse {
  access_token: string;
  token_type: string;
}

export default function Home() {
  // --- STATE ---
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [token, setToken] = useState("");

  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceSummary | null>(null);
  const [portfolioItems, setPortfolioItems] = useState<PortfolioItem[]>([]);
  const [engagementItems, setEngagementItems] = useState<EngagementItem[]>([]);
  const [businessUnitFilter, setBusinessUnitFilter] = useState("");
  const [proposalSow, setProposalSow] = useState<ProposalSowPayload | null>(null);
  const [workspaceMessage, setWorkspaceMessage] = useState("");
  const [workspaceBusy, setWorkspaceBusy] = useState(false);
  const [workspaceMembers, setWorkspaceMembers] = useState<WorkspaceMember[]>([]);
  const [memberMessage, setMemberMessage] = useState("");
  const [memberBusy, setMemberBusy] = useState(false);

  const [activeTab, setActiveTab] = useState("dashboard"); // dashboard, members, intake, upload, insights
  const [insightsSubTab, setInsightsSubTab] = useState("summary"); // summary, bottlenecks, opportunity, matrix, scoring, risks, pilot, roadmap, export, commercial, investment
  const [activeArchLayer, setActiveArchLayer] = useState("systems");
  const [investmentPackage, setInvestmentPackage] = useState<InvestmentPackage | null>(null);
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<number | null>(null);
  const [financeDraft, setFinanceDraft] = useState({
    monthly_volume: "",
    effort_minutes_per_transaction: "",
    loaded_hourly_cost: "",
    automation_rate: "",
    adoption_rate: "",
    implementation_cost: "",
    integration_cost: "",
    cloud_llm_monthly_cost: "",
    currency: "USD",
  });
  const [investmentBusy, setInvestmentBusy] = useState(false);
  const [investmentMessage, setInvestmentMessage] = useState("");
  const [decisionDraft, setDecisionDraft] = useState({ status: "validate_first", explanation: "" });
  
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [clients, setClients] = useState<ClientWorkspace[]>([]);
  const [selectedAssessment, setSelectedAssessment] = useState<Assessment | null>(null);
  const [selectedClientId, setSelectedClientId] = useState("");
  
  // Intake Form
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("Professional Services");
  const [companySize, setCompanySize] = useState("100-500 employees");
  const [departments, setDepartments] = useState<string[]>([]);
  const [tools, setTools] = useState<string[]>([]);
  const [cloudPref, setCloudPref] = useState("Azure");
  const [compliance, setCompliance] = useState<string[]>([]);
  const [goalsText, setGoalsText] = useState("");
  const [painPoints, setPainPoints] = useState<string[]>([]);
  const [aiGoals, setAiGoals] = useState<string[]>([]);

  // File Upload State
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Human Review Mode
  const [isReviewMode, setIsReviewMode] = useState(false);
  
  // API loader
  const [loading, setLoading] = useState(false);

  // Dynamically calculated command center outcomes:
  const overallScore = selectedAssessment ? int(selectedAssessment.overall_score) : 0;
  const highValueOpportunities = selectedAssessment?.use_cases?.filter(u => u.value === "High").length ?? 0;
  const quickWinPilots = selectedAssessment?.use_cases?.filter(u => u.value === "High" && u.complexity === "Low").length ?? 0;
  const governanceRisksCount = selectedAssessment?.risks?.filter(r => r.severity === "High" || r.severity === "Medium").length ?? 0;
  const automationPotentialVal = selectedAssessment ? int(selectedAssessment.automation_potential) : 0;
  const recommendedFirstPilotName = selectedAssessment?.recommended_first_pilot ?? "TBD";
  const riskLevelVal = selectedAssessment?.risk_level ?? "Low";
  const currentApprovalStatusVal = selectedAssessment?.approval_status ?? "draft";

  const DIMENSION_WEIGHTS: Record<string, number> = {
    data_readiness: 0.20,
    process_readiness: 0.15,
    integration_readiness: 0.15,
    governance_readiness: 0.15,
    security_readiness: 0.15,
    team_readiness: 0.10,
    business_alignment: 0.10,
  };

  const recomputeWeightedOverall = (assessment: Assessment) => {
    let total = 0;
    for (const [key, weight] of Object.entries(DIMENSION_WEIGHTS)) {
      total += int(assessment[key as keyof Assessment] as number) * weight;
    }
    return Math.round(total * 10) / 10;
  };

  const getReadinessDimensionExplanation = (subject: string, score: number, key?: string) => {
    const details = key ? selectedAssessment?.dimension_score_details?.[key] : undefined;
    const backendJustification = key ? getDimensionJustification(key) : null;
    const missing = details?.missing_information || [];
    const flags = details?.estimate_flags || [];
    const refs = details?.evidence_refs || [];
    const insufficient = Boolean(selectedAssessment?.insufficient_evidence);
    const uncertainty = insufficient
      ? "Uncertainty: insufficient document evidence — treat this score as provisional."
      : flags.length
        ? `Uncertainty: ${flags.join(", ").replaceAll("_", " ")}.`
        : refs.length
          ? `Grounded in ${refs.length} cited evidence item(s); still subject to human review.`
          : "Uncertainty: limited cited evidence for this dimension.";

    const explanation = backendJustification
      ? `${backendJustification} ${uncertainty}`
      : `Score ${int(score)}/100 for ${subject} is derived from intake signals and document-observed cues. ${uncertainty}`;

    const recommendation = missing.length
      ? `Missing evidence to close: ${missing.slice(0, 2).join(" ")}`
      : "Validate this dimension with a human reviewer before external client delivery.";

    return { explanation, recommendation, missing, refs, uncertainty };
  };

  // --- PROCESSING STEPS ---
  const steps = [
    "Analyzing documents...",
    "Extracting business processes...",
    "Identifying repetitive workflows...",
    "Mapping data sources...",
    "Detecting AI automation opportunities...",
    "Checking governance gaps...",
    "Generating readiness score..."
  ];

  // --- INITIAL SEEDS ---
  useEffect(() => {
    // Attempt auto-login if token in localStorage
    const savedToken = localStorage.getItem("token");
    if (savedToken) {
      setToken(savedToken);
      setIsLoggedIn(true);
    }
  }, []);

  const getAuthHeaders = useCallback((includeJson = false): HeadersInit => {
    const headers: Record<string, string> = {};
    if (includeJson) {
      headers["Content-Type"] = "application/json";
    }
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  }, [token]);

  const parseErrorMessage = async (res: Response, fallback: string) => {
    try {
      const payload = await res.json();
      return payload.detail || fallback;
    } catch {
      return fallback;
    }
  };

  // --- API FUNCTIONS ---
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      const formData = new FormData();
      formData.append("username", email);
      formData.append("password", password);

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Authentication failed");
      }

      const data: AuthTokenResponse = await res.json();
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setIsLoggedIn(true);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Invalid credentials");
    }
  };

  const handleDemoAccess = () => {
    setEmail("demo@studio.com");
    setPassword("password123");
    // Trigger login
    setTimeout(() => {
      const form = document.getElementById("login-form");
      if (form) {
        form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      }
    }, 100);
  };

  const handleLogout = useCallback(() => {
    localStorage.removeItem("token");
    setToken("");
    setIsLoggedIn(false);
    setActiveTab("dashboard");
    setSelectedAssessment(null);
    setAssessments([]);
    setClients([]);
  }, []);

  const loadAssessments = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/assessments/`, {
        headers: getAuthHeaders(),
      });

      if (res.status === 401) {
        handleLogout();
        return;
      }

      if (!res.ok) {
        throw new Error(await parseErrorMessage(res, "Could not load assessments"));
      }

      const loadedAssessments: Assessment[] = await res.json();
      if (loadedAssessments.length > 0) {
        setAssessments(loadedAssessments);
        setSelectedAssessment((current) => {
          if (!current) {
            return loadedAssessments[0];
          }

          return loadedAssessments.find((item) => item.id === current.id) ?? loadedAssessments[0];
        });
        return;
      }

      // Optional demo workspace seed — skipped when backend disables demo mode.
      const demoRes = await fetch(`${API_BASE}/assessments/demo`, {
        method: "POST",
        headers: getAuthHeaders(),
      });
      if (demoRes.status === 403) {
        setAssessments([]);
        setSelectedAssessment(null);
        return;
      }
      if (!demoRes.ok) {
        throw new Error(await parseErrorMessage(demoRes, "Could not create demo assessment"));
      }

      const demoData: Assessment = await demoRes.json();
      if (demoData.client) {
        setClients((current) => [demoData.client as ClientWorkspace, ...current.filter((item) => item.id !== demoData.client?.id)]);
      }
      setAssessments([demoData]);
      setSelectedAssessment(demoData);
    } catch (e) {
      console.warn("Could not seed demo via backend: ", e);
      setAssessments([]);
      setSelectedAssessment(null);
    } finally {
      setLoading(false);
    }
  }, [token, handleLogout, getAuthHeaders]);

  const loadClients = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/clients/`, {
        headers: getAuthHeaders(),
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        throw new Error(await parseErrorMessage(res, "Could not load clients"));
      }
      const loadedClients: ClientWorkspace[] = await res.json();
      setClients(loadedClients);
    } catch (err) {
      console.error(err);
    }
  }, [token, handleLogout, getAuthHeaders]);


  const loadWorkspaces = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/workspaces/`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error(await parseErrorMessage(res, "Could not load workspaces"));
      const data: WorkspaceSummary[] = await res.json();
      setWorkspaces(data);
      setSelectedWorkspace((current) => {
        if (current && data.some((w) => w.id === current.id)) {
          return data.find((w) => w.id === current.id) || data[0] || null;
        }
        return data[0] || null;
      });
    } catch (err) {
      console.error(err);
    }
  }, [token, getAuthHeaders]);

  const loadWorkspaceViews = useCallback(async (workspaceId: number) => {
    try {
      const [portfolioRes, engRes] = await Promise.all([
        fetch(`${API_BASE}/workspaces/${workspaceId}/portfolio`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/workspaces/${workspaceId}/engagements`, { headers: getAuthHeaders() }),
      ]);
      if (portfolioRes.ok) {
        const portfolio = await portfolioRes.json();
        setPortfolioItems(portfolio.assessments || portfolio.items || []);
      }
      if (engRes.ok) {
        const eng = await engRes.json();
        setEngagementItems(eng.engagements || []);
      }
    } catch (err) {
      console.error(err);
    }
  }, [getAuthHeaders]);

  const loadWorkspaceMembers = useCallback(async (workspaceId: number) => {
    try {
      const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/members`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        setWorkspaceMembers([]);
        return;
      }
      setWorkspaceMembers(await res.json());
    } catch (err) {
      console.error(err);
      setWorkspaceMembers([]);
    }
  }, [getAuthHeaders]);

  const handleAddWorkspaceMember = async (payload: {
    email: string;
    role: string;
    full_name?: string;
    temporary_password?: string;
    authorized_client_ids?: number[];
  }) => {
    if (!selectedWorkspace?.id) return;
    setMemberBusy(true);
    setMemberMessage("");
    try {
      const res = await fetch(`${API_BASE}/workspaces/${selectedWorkspace.id}/members`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await parseErrorMessage(res, "Could not add member"));
      setMemberMessage(`Added ${payload.email} as ${payload.role}`);
      await loadWorkspaceMembers(selectedWorkspace.id);
    } catch (err) {
      setMemberMessage(err instanceof Error ? err.message : "Could not add member");
    } finally {
      setMemberBusy(false);
    }
  };

  const handleUpdateWorkspaceMember = async (
    userId: number,
    payload: { role: string; authorized_client_ids?: number[] | null }
  ) => {
    if (!selectedWorkspace?.id) return;
    setMemberBusy(true);
    setMemberMessage("");
    try {
      const res = await fetch(
        `${API_BASE}/workspaces/${selectedWorkspace.id}/members/${userId}`,
        {
          method: "PUT",
          headers: getAuthHeaders(true),
          body: JSON.stringify(payload),
        }
      );
      if (!res.ok) throw new Error(await parseErrorMessage(res, "Could not update member"));
      setMemberMessage("Member access updated");
      await loadWorkspaceMembers(selectedWorkspace.id);
    } catch (err) {
      setMemberMessage(err instanceof Error ? err.message : "Could not update member");
    } finally {
      setMemberBusy(false);
    }
  };

  const loadProposalSow = useCallback(async (assessmentId: number) => {
    try {
      const res = await fetch(`${API_BASE}/workspaces/assessments/${assessmentId}/proposal-sow`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setProposalSow(await res.json());
      } else {
        setProposalSow(null);
      }
    } catch {
      setProposalSow(null);
    }
  }, [getAuthHeaders]);

  const handleGenerateProposalSow = async (feeEstimate: Record<string, unknown>) => {
    if (!selectedAssessment) return;
    setWorkspaceBusy(true);
    setWorkspaceMessage("");
    try {
      const res = await fetch(`${API_BASE}/workspaces/assessments/${selectedAssessment.id}/proposal-sow`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify({ fee_estimate: feeEstimate }),
      });
      if (!res.ok) throw new Error(await parseErrorMessage(res, "Could not generate proposal/SOW"));
      const data = await res.json();
      setProposalSow({
        proposal_package: data.proposal_package,
        sow_package: data.sow_package,
        fee_estimate: feeEstimate,
        complete: true,
      });
      setWorkspaceMessage("Proposal/SOW draft generated. Fees remain separate from modeled ROI.");
      if (selectedWorkspace?.id) loadWorkspaceViews(selectedWorkspace.id);
    } catch (err) {
      setWorkspaceMessage(err instanceof Error ? err.message : "Proposal generation failed");
    } finally {
      setWorkspaceBusy(false);
    }
  };

  const handleExportProposalSow = async () => {
    if (!selectedAssessment) return;
    setWorkspaceBusy(true);
    try {
      const res = await fetch(`${API_BASE}/assessments/${selectedAssessment.id}/export/proposal-sow`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error(await parseErrorMessage(res, "Could not export proposal/SOW"));
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedAssessment.company_name.replace(/\s+/g, "_")}_Proposal_SOW.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setWorkspaceMessage(err instanceof Error ? err.message : "Export failed");
    } finally {
      setWorkspaceBusy(false);
    }
  };

  const handleWorkflowUpdate = async (status: string, reason: string) => {
    if (!selectedAssessment) return;
    setWorkspaceBusy(true);
    setWorkspaceMessage("");
    try {
      const res = await fetch(`${API_BASE}/workspaces/assessments/${selectedAssessment.id}/workflow`, {
        method: "PUT",
        headers: getAuthHeaders(true),
        body: JSON.stringify({ workflow_status: status, reason }),
      });
      if (!res.ok) throw new Error(await parseErrorMessage(res, "Could not update workflow"));
      const data = await res.json();
      setSelectedAssessment({
        ...selectedAssessment,
        workflow_status: data.workflow_status,
        locked_for_delivery: data.locked_for_delivery ? 1 : 0,
      } as Assessment);
      setWorkspaceMessage(`Workflow updated to ${data.workflow_status}`);
      if (selectedWorkspace?.id) loadWorkspaceViews(selectedWorkspace.id);
    } catch (err) {
      setWorkspaceMessage(err instanceof Error ? err.message : "Workflow update failed");
    } finally {
      setWorkspaceBusy(false);
    }
  };

  // Trigger seeding Apex Consulting instantly on dashboard load
  useEffect(() => {
    if (isLoggedIn) {
      loadClients();
      loadAssessments();
      loadWorkspaces();
    }
  }, [isLoggedIn, loadAssessments, loadClients, loadWorkspaces]);

  useEffect(() => {
    if (selectedWorkspace?.id) {
      loadWorkspaceViews(selectedWorkspace.id);
      loadWorkspaceMembers(selectedWorkspace.id);
    }
  }, [selectedWorkspace?.id, loadWorkspaceViews, loadWorkspaceMembers]);

  useEffect(() => {
    if (selectedAssessment?.id && insightsSubTab === "proposal") {
      loadProposalSow(selectedAssessment.id);
    }
  }, [selectedAssessment?.id, insightsSubTab, loadProposalSow]);

  // Demo auto fill trigger
  const handleIntakeAutoFill = () => {
    setSelectedClientId("");
    setCompanyName("Apex Global Consulting Partners");
    setIndustry("Professional Services");
    setCompanySize("100-500 employees");
    setDepartments(["Operations", "Customer Support", "Sales & Pre-sales", "Compliance & Governance"]);
    setTools(["Salesforce", "Microsoft Excel", "Jira Service Desk", "SharePoint"]);
    setCloudPref("Azure");
    setCompliance(["GDPR", "SOC2 Type II"]);
    setGoalsText("Automate redundant pre-sales proposal drafting and support ticket parsing to optimize service delivery speeds.");
    setPainPoints(["Manual Process Overload", "Data Silos", "Slow Support Response Times"]);
    setAiGoals(["Efficiency / Cost Reduction", "Enhanced Customer Experience"]);
  };

  const buildSyntheticAssessmentBrief = useCallback(() => {
    const targetName = selectedAssessment?.company_name || companyName || "Prospective client";
    const targetIndustry = selectedAssessment?.industry || industry;
    const targetDepartments = (selectedAssessment?.departments?.length ? selectedAssessment.departments : departments).join(", ") || "Operations";
    const targetTools = (selectedAssessment?.current_tools?.length ? selectedAssessment.current_tools : tools).join(", ") || "Salesforce, SharePoint";
    const targetCompliance = (selectedAssessment?.compliance_requirements?.length ? selectedAssessment.compliance_requirements : compliance).join(", ") || "GDPR";
    const targetPainPoints = (selectedAssessment?.pain_points?.length ? selectedAssessment.pain_points : painPoints).join(", ") || "Manual Process Overload";
    const targetGoals = selectedAssessment?.main_business_goals || goalsText || "Improve service delivery speed";
    const targetAiGoals = (selectedAssessment?.ai_goals?.length ? selectedAssessment.ai_goals : aiGoals).join(", ") || "Efficiency / Cost Reduction";

    return [
      `Company: ${targetName}`,
      `Industry: ${targetIndustry}`,
      `Departments in scope: ${targetDepartments}`,
      `Current tools: ${targetTools}`,
      `Compliance requirements: ${targetCompliance}`,
      `Primary pain points: ${targetPainPoints}`,
      `Business goals: ${targetGoals}`,
      `AI goals: ${targetAiGoals}`,
      "Observed workflow signals:",
      "- Teams reuse prior proposals, operating notes, and support responses across engagements.",
      "- Knowledge is distributed across shared files and manual reviewer handoffs.",
      "- Leadership wants a first pilot that improves delivery speed without increasing governance risk.",
    ].join("\n");
  }, [selectedAssessment, companyName, industry, departments, tools, compliance, goalsText, painPoints, aiGoals]);

  // Submit Intake Form & Start processing
  const handleIntakeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName) return;

    setLoading(true);
    try {
      const payload = {
        client_id: selectedClientId ? parseInt(selectedClientId, 10) : null,
        company_name: companyName,
        industry,
        company_size: companySize,
        departments,
        current_tools: tools,
        cloud_preference: cloudPref,
        compliance_requirements: compliance,
        main_business_goals: goalsText,
        pain_points: painPoints,
        ai_goals: aiGoals
      };

      const res = await fetch(`${API_BASE}/assessments/`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const ass: Assessment = await res.json();
        if (ass.client) {
          setClients((current) => [ass.client as ClientWorkspace, ...current.filter((item) => item.id !== ass.client?.id)]);
          setSelectedClientId(String(ass.client.id));
        }
        setSelectedAssessment(ass);
        setAssessments((current) => [ass, ...current.filter((item) => item.id !== ass.id)]);
        setActiveTab("upload");
      } else {
        throw new Error(await parseErrorMessage(res, "Could not create assessment"));
      }
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Could not create assessment");
    } finally {
      setLoading(false);
    }
  };

  // Start analysis simulation + trigger backend LangGraph sequence
  const handleFileUploadAndRun = async () => {
    if (!selectedAssessment) return;
    setIsProcessing(true);
    setProcessingStep(0);
    setUploadProgress(10);

    // Simulate animated extraction step loops
    const stepInterval = setInterval(() => {
      setProcessingStep(prev => {
        if (prev < steps.length - 1) {
          return prev + 1;
        } else {
          clearInterval(stepInterval);
          return prev;
        }
      });
      setUploadProgress(prev => Math.min(95, prev + 12));
    }, 1200);

    try {
      const formData = new FormData();
      if (selectedFiles.length > 0) {
        selectedFiles.forEach(file => {
          formData.append("files", file);
        });
      } else {
        // Feed a richer synthetic brief so demo-mode analysis stays aligned to the intake context.
        const syntheticBrief = buildSyntheticAssessmentBrief();
        const blob = new Blob([syntheticBrief], { type: "text/plain" });
        const fallbackName = `${selectedAssessment.company_name.replace(/\s+/g, "_").toLowerCase()}_brief.txt`;
        formData.append("files", new File([blob], fallbackName));
      }

      const res = await fetch(`${API_BASE}/assessments/${selectedAssessment.id}/upload`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData
      });

      if (res.ok) {
        const finishedAss: Assessment = await res.json();
        clearInterval(stepInterval);
        setUploadProgress(100);
        setTimeout(() => {
          setSelectedAssessment(finishedAss);
          setAssessments((current) => current.map((item) => item.id === finishedAss.id ? finishedAss : item));
          setIsProcessing(false);
          setActiveTab("insights");
          setInsightsSubTab("summary");
        }, 800);
      } else {
        throw new Error("LangGraph processing failed");
      }
    } catch (err) {
      console.error(err);
      setIsProcessing(false);
      clearInterval(stepInterval);
      alert("AI pipeline encountered a network fallback. Loading preloaded sample client workspace.");
      // Load seeded demo instead
      loadAssessments();
      setActiveTab("insights");
    }
  };

  // Handle Human Review Mode modifications and save to database
  const handleReviewSave = async () => {
    if (!selectedAssessment) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/assessments/${selectedAssessment.id}`, {
        method: "PUT",
        headers: getAuthHeaders(true),
        body: JSON.stringify(selectedAssessment)
      });
      if (res.ok) {
        const updated: Assessment = await res.json();
        setSelectedAssessment(updated);
        setAssessments((current) => current.map((item) => item.id === updated.id ? updated : item));
        setIsReviewMode(false);
      } else {
        throw new Error(await parseErrorMessage(res, "Could not save manual edits"));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const applyInvestmentPackage = (pkg: InvestmentPackage) => {
    setInvestmentPackage(pkg);
    const opps = pkg.opportunities || [];
    const selected =
      opps.find((o) => o.pilot_selected) ||
      opps.find((o) => o.ranking === 1) ||
      opps[0];
    setSelectedOpportunityId(selected?.id ?? null);
    const inputs = (selected?.financial_inputs || {}) as Record<string, unknown>;
    setFinanceDraft({
      monthly_volume: inputs.monthly_volume != null ? String(inputs.monthly_volume) : "",
      effort_minutes_per_transaction:
        inputs.effort_minutes_per_transaction != null
          ? String(inputs.effort_minutes_per_transaction)
          : "",
      loaded_hourly_cost:
        inputs.loaded_hourly_cost != null ? String(inputs.loaded_hourly_cost) : "",
      automation_rate: inputs.automation_rate != null ? String(inputs.automation_rate) : "",
      adoption_rate: inputs.adoption_rate != null ? String(inputs.adoption_rate) : "",
      implementation_cost:
        inputs.implementation_cost != null ? String(inputs.implementation_cost) : "",
      integration_cost:
        inputs.integration_cost != null ? String(inputs.integration_cost) : "",
      cloud_llm_monthly_cost:
        inputs.cloud_llm_monthly_cost != null ? String(inputs.cloud_llm_monthly_cost) : "",
      currency: String(inputs.currency || "USD"),
    });
    setDecisionDraft({
      status: pkg.decision_summary?.status || "validate_first",
      explanation: pkg.decision_summary?.explanation || "",
    });
  };

  const loadInvestmentIntelligence = useCallback(async (assessmentId: number) => {
    setInvestmentBusy(true);
    setInvestmentMessage("");
    try {
      const res = await fetch(
        `${API_BASE}/assessments/${assessmentId}/investment-intelligence`,
        { headers: getAuthHeaders() }
      );
      if (!res.ok) {
        throw new Error(await parseErrorMessage(res, "Could not load investment intelligence"));
      }
      const pkg: InvestmentPackage = await res.json();
      applyInvestmentPackage(pkg);
    } catch (err) {
      console.error(err);
      setInvestmentMessage(err instanceof Error ? err.message : "Investment load failed");
    } finally {
      setInvestmentBusy(false);
    }
  }, [getAuthHeaders]);

  useEffect(() => {
    if (insightsSubTab === "investment" && selectedAssessment?.id) {
      loadInvestmentIntelligence(selectedAssessment.id);
    }
  }, [insightsSubTab, selectedAssessment?.id, loadInvestmentIntelligence]);

  const saveOpportunityFinancials = async () => {
    if (!selectedAssessment || !selectedOpportunityId) return;
    setInvestmentBusy(true);
    setInvestmentMessage("");
    try {
      const financial_inputs: Record<string, unknown> = {
        currency: financeDraft.currency || "USD",
        provenance: {
          monthly_volume: "client_provided_estimate",
          effort_minutes_per_transaction: "client_provided_estimate",
          loaded_hourly_cost: "consultant_assumption",
          automation_rate: "consultant_assumption",
          adoption_rate: "consultant_assumption",
          implementation_cost: "consultant_assumption",
          integration_cost: "consultant_assumption",
          cloud_llm_monthly_cost: "consultant_assumption",
        },
      };
      (
        [
          "monthly_volume",
          "effort_minutes_per_transaction",
          "loaded_hourly_cost",
          "automation_rate",
          "adoption_rate",
          "implementation_cost",
          "integration_cost",
          "cloud_llm_monthly_cost",
        ] as const
      ).forEach((key) => {
        const raw = financeDraft[key];
        if (raw !== "") financial_inputs[key] = Number(raw);
      });
      const res = await fetch(
        `${API_BASE}/assessments/${selectedAssessment.id}/investment-intelligence/opportunities/${selectedOpportunityId}/financials`,
        {
          method: "PUT",
          headers: getAuthHeaders(true),
          body: JSON.stringify({
            financial_inputs,
            reason: "Updated financial assumptions from Investment Intelligence panel",
          }),
        }
      );
      if (!res.ok) {
        throw new Error(await parseErrorMessage(res, "Could not recalculate financials"));
      }
      applyInvestmentPackage(await res.json());
      setInvestmentMessage("Financial model recalculated from updated assumptions.");
    } catch (err) {
      setInvestmentMessage(err instanceof Error ? err.message : "Financial update failed");
    } finally {
      setInvestmentBusy(false);
    }
  };

  const saveInvestmentDecision = async () => {
    if (!selectedAssessment) return;
    setInvestmentBusy(true);
    try {
      const res = await fetch(
        `${API_BASE}/assessments/${selectedAssessment.id}/investment-intelligence/decision`,
        {
          method: "PUT",
          headers: getAuthHeaders(true),
          body: JSON.stringify(decisionDraft),
        }
      );
      if (!res.ok) {
        throw new Error(await parseErrorMessage(res, "Could not save investment decision"));
      }
      applyInvestmentPackage(await res.json());
      setInvestmentMessage("Investment decision recorded with reviewer audit trail.");
    } catch (err) {
      setInvestmentMessage(err instanceof Error ? err.message : "Decision save failed");
    } finally {
      setInvestmentBusy(false);
    }
  };

  // File download helper
  const handleDownload = async (format: string) => {
    if (!selectedAssessment) return;
    try {
      const res = await fetch(`${API_BASE}/assessments/${selectedAssessment.id}/export/${format}`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        throw new Error(await parseErrorMessage(res, `Could not export ${format.toUpperCase()}`));
      }

      const blob = await res.blob();
      const contentDisposition = res.headers.get("content-disposition");
      const fallbackName = `${selectedAssessment.company_name.replace(/\s+/g, "_")}.${format}`;
      const fileName = contentDisposition?.match(/filename="?([^"]+)"?/)?.[1] ?? fallbackName;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Download failed");
    }
  };

  const handleDeleteAssessment = async (assessmentId: number) => {
    const shouldDelete = window.confirm("Delete this assessment workspace?");
    if (!shouldDelete) return;

    try {
      const res = await fetch(`${API_BASE}/assessments/${assessmentId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        throw new Error(await parseErrorMessage(res, "Could not delete assessment"));
      }

      setAssessments((current) => current.filter((item) => item.id !== assessmentId));
      setSelectedAssessment((current) => current?.id === assessmentId ? null : current);
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  // Multi-select lists triggers
  const toggleSelection = (item: string, list: string[], setList: React.Dispatch<React.SetStateAction<string[]>>) => {
    if (list.includes(item)) {
      setList(list.filter(x => x !== item));
    } else {
      setList([...list, item]);
    }
  };

  // Recharts scoring package formatter
  const getRadarData = () => {
    if (!selectedAssessment) return [];
    return [
      { subject: "Data Readiness", A: selectedAssessment.data_readiness, justification: selectedAssessment.data_justification },
      { subject: "Process Readiness", A: selectedAssessment.process_readiness, justification: selectedAssessment.process_justification },
      { subject: "Integration Readiness", A: selectedAssessment.integration_readiness, justification: selectedAssessment.integration_justification },
      { subject: "Governance Readiness", A: selectedAssessment.governance_readiness, justification: selectedAssessment.governance_justification },
      { subject: "Security Readiness", A: selectedAssessment.security_readiness, justification: selectedAssessment.security_justification },
      { subject: "Team Readiness", A: selectedAssessment.team_readiness, justification: selectedAssessment.team_justification },
      { subject: "Business Alignment", A: selectedAssessment.business_alignment, justification: selectedAssessment.alignment_justification }
    ];
  };

  const getBarData = () => {
    return getRadarData();
  };

  const getDimensionJustification = (key: string) => {
    if (!selectedAssessment) return null;
    const justificationMap: Record<string, string | null> = {
      data_readiness: selectedAssessment.data_justification,
      process_readiness: selectedAssessment.process_justification,
      integration_readiness: selectedAssessment.integration_justification,
      governance_readiness: selectedAssessment.governance_justification,
      security_readiness: selectedAssessment.security_justification,
      team_readiness: selectedAssessment.team_justification,
      business_alignment: selectedAssessment.alignment_justification,
    };
    return justificationMap[key] ?? null;
  };

  const selectedClient = selectedClientId
    ? clients.find((client) => client.id === parseInt(selectedClientId, 10)) ?? null
    : null;

  const knownClients = [
    ...clients,
    ...assessments
      .map((assessment) => assessment.client)
      .filter((client): client is ClientWorkspace => client !== null && !clients.some((known) => known.id === client.id)),
  ];

  const clientWorkspaceGroups = [
    ...knownClients.map((client) => ({
      client,
      assessments: assessments.filter((assessment) => assessment.client_id === client.id),
    })),
    {
      client: null,
      assessments: assessments.filter((assessment) => assessment.client_id == null),
    },
  ].filter((group) => group.assessments.length > 0);

  const evidenceHighlights = selectedAssessment?.extracted_signals?.slice(0, 3) ?? [];
  const isDemoModeEvidence = evidenceHighlights.length > 0 && evidenceHighlights.every((signal) => signal.source_file.includes("_brief") || signal.source_file.startsWith("dummy_"));
  const isDocumentGrounded = evidenceHighlights.length > 0 && !isDemoModeEvidence;
  const approvalStatus = selectedAssessment?.approval_status ?? "draft";
  const canExport = approvalStatus === "approved";

  const getApprovalStatusBadge = (status: string) => {
    if (status === "approved") {
      return "border-emerald-500/20 bg-emerald-950/20 text-emerald-300";
    }
    if (status === "reviewed") {
      return "border-blue-500/20 bg-blue-950/20 text-blue-300";
    }
    return "border-amber-500/20 bg-amber-950/20 text-amber-300";
  };

  // Grid coordinates mapping for Prioritization Matrix use cases
  const mapMatrixCoordinates = (value: string, complexity: string) => {
    let x = 50; // Complexity (Low=25, Med=50, High=75)
    let y = 50; // Value (Low=75, Med=50, High=25 - inverted for standard quadrant top=high)
    
    if (complexity === "Low") x = 25;
    if (complexity === "Medium") x = 50;
    if (complexity === "High") x = 75;

    if (value === "Low") y = 75;
    if (value === "Medium") y = 50;
    if (value === "High") y = 25;

    return { x, y };
  };

  // --- COMMERCIAL STRATEGY HELPERS ---
  const getEngagementRecommendation = () => {
    if (!selectedAssessment) return {
      model: "Pilot MVP Build",
      pilotName: "Intelligent Pre-Sales Proposal Copilot",
      pricingRange: "₹6L – ₹18L",
      priceMin: 600000,
      priceMax: 1800000,
      rationale: "Initial pilot recommendations pending database loading.",
      teamType: "Pilot MVP Build"
    };

    const company = selectedAssessment.company_name || "";
    const isApex = company.toLowerCase().includes("apex");
    const useCasesCount = selectedAssessment.use_cases?.length ?? 0;
    const deptCount = selectedAssessment.departments?.length ?? 0;
    
    // safe dynamic scores sum
    const dScore = selectedAssessment.data_readiness ?? 60;
    const pScore = selectedAssessment.process_readiness ?? 60;
    const iScore = selectedAssessment.integration_readiness ?? 60;
    const gScore = selectedAssessment.governance_readiness ?? 60;
    const sScore = selectedAssessment.security_readiness ?? 60;
    const tScore = selectedAssessment.team_readiness ?? 60;
    const bScore = selectedAssessment.business_alignment ?? 60;
    const avgScore = Math.round((dScore + pScore + iScore + gScore + sScore + tScore + bScore) / 7);

    // Apex walkthrough workspace overrides
    if (isApex) {
      return {
        model: "Pilot MVP Build",
        pilotName: "Intelligent Pre-Sales Proposal Copilot",
        pricingRange: "₹6L – ₹18L",
        priceMin: 600000,
        priceMax: 1800000,
        rationale: "The client has clear Sales & Pre-sales bottlenecks, highly structured reusable proposal playbooks, and a high-value / low-complexity P1 first pilot opportunity.",
        teamType: "Pilot MVP Build"
      };
    }

    // Dynamic heuristics
    if (avgScore < 50) {
      return {
        model: "AI Readiness Sprint",
        pilotName: selectedAssessment.recommended_first_pilot || "Transformation Strategy Blueprint",
        pricingRange: "₹1.5L – ₹5L",
        priceMin: 150000,
        priceMax: 500000,
        rationale: `With an overall AI readiness score of ${avgScore}/100, foundational data and alignment gaps should be resolved prior to direct engineering.`,
        teamType: "AI Readiness Sprint"
      };
    } else if ((selectedAssessment.compliance_requirements?.length ?? 0) > 1 && gScore < 50) {
      return {
        model: "Managed AI Governance Retainer",
        pilotName: "AI Compliance & Audit Framework",
        pricingRange: "₹2L – ₹8L per month",
        priceMin: 200000,
        priceMax: 800000,
        rationale: `Rigid compliance mandates (${selectedAssessment.compliance_requirements?.join(", ") ?? "GDPR/SOC2"}) and low governance readiness (${gScore}/100) call for ongoing expert oversight.`,
        teamType: "Managed AI Governance Retainer"
      };
    } else if (tScore < 45) {
      return {
        model: "AI Enablement + Training Program",
        pilotName: "Enterprise AI Enablement Series",
        pricingRange: "₹3L – ₹12L",
        priceMin: 300000,
        priceMax: 1200000,
        rationale: `Low team readiness score (${tScore}/100) indicates that human training and pilot adoption gates are key to project success.`,
        teamType: "AI Enablement + Training Program"
      };
    } else if (avgScore > 75 && useCasesCount > 2) {
      return {
        model: "Production Rollout",
        pilotName: selectedAssessment.recommended_first_pilot || "Cross-Department Production AI Nodes",
        pricingRange: "₹20L – ₹75L+",
        priceMin: 2000000,
        priceMax: 7500000,
        rationale: `High readiness score (${avgScore}/100) across ${deptCount} departments warrants a scalable production deployment of the opportunities catalog.`,
        teamType: "Production Rollout"
      };
    } else {
      return {
        model: "Pilot MVP Build",
        pilotName: selectedAssessment.recommended_first_pilot || "Intelligent Pre-Sales Proposal Copilot",
        pricingRange: "₹6L – ₹18L",
        priceMin: 600000,
        priceMax: 1800000,
        rationale: `Grounded use cases and solid alignment metrics support launching a practical, low-complexity initial pilot to build organizational trust.`,
        teamType: "Pilot MVP Build"
      };
    }
  };

  const getCalibratedPricing = (rec: { model: string; pilotName: string; pricingRange: string; priceMin: number; priceMax: number; rationale: string; teamType: string; }) => {
    if (!selectedAssessment) return rec.pricingRange;

    let baseMin = rec.priceMin;
    let baseMax = rec.priceMax;

    // Adjust price dynamically based on scope
    const deptCount = selectedAssessment.departments?.length ?? 0;
    const complianceCount = selectedAssessment.compliance_requirements?.length ?? 0;
    const iScore = selectedAssessment.integration_readiness ?? 60;
    
    // Add ₹50,000 for each department beyond 1
    if (deptCount > 1) {
      baseMin += (deptCount - 1) * 50000;
      baseMax += (deptCount - 1) * 100000;
    }

    // Add ₹75,000 for each compliance requirement that adds review steps
    if (complianceCount > 0) {
      baseMin += complianceCount * 75000;
      baseMax += complianceCount * 150000;
    }

    // Adjust for integration readiness score (low integration readiness = more middleware mapping needed = higher price)
    if (iScore < 50) {
      baseMin += 80000;
      baseMax += 150000;
    }

    // Format output cleanly in Lakhs
    const formatLakh = (val: number) => {
      const lakhs = val / 100000;
      return `₹${lakhs.toFixed(1)}L`;
    };

    return rec.model === "Managed AI Governance Retainer" 
      ? `${formatLakh(baseMin)} – ${formatLakh(baseMax)} per month` 
      : `${formatLakh(baseMin)} – ${formatLakh(baseMax)}`;
  };

  const getPricingJustifications = () => {
    if (!selectedAssessment) return [];

    const company = selectedAssessment.company_name || "";
    const isApex = company.toLowerCase().includes("apex");

    if (isApex) {
      return [
        { title: "Sales & Pre-sales", desc: "Intelligent Pre-Sales Proposal Copilot requires RAG semantic parsing over proprietary solution playbooks." },
        { title: "Customer Support", desc: "Autonomous Support Triage Router demands layout classification and incident log parsing." },
        { title: "Integrations in Scope", desc: "API integrations mapping Salesforce pipeline context, SharePoint files, and Jira webhooks." },
        { title: "Compliance Checkpoints", desc: "GDPR policy checks and SOC2 Type II metadata auditing require secure tenant scoping." },
        { title: "Strategic Asset Generator", desc: "Custom-branded PDF Readiness Reports and Executive Board PPTX export integrations." },
        { title: "Human Review Workflow", desc: "Draft-to-Approved human-in-the-loop validation screens to prevent operational model hallucinations." }
      ];
    }

    const factors = [];
    // Dynamic factors based on actual assessment fields
    if ((selectedAssessment.departments?.length ?? 0) > 0) {
      factors.push({
        title: `${selectedAssessment.departments.length} Department(s) in Scope`,
        desc: `Custom workflows mapping context across ${selectedAssessment.departments.join(", ")}.`
      });
    }
    if ((selectedAssessment.compliance_requirements?.length ?? 0) > 0) {
      factors.push({
        title: "Compliance Governance Controls",
        desc: `Requires security scoping matching compliance policies for ${selectedAssessment.compliance_requirements.join(", ")}.`
      });
    }
    if ((selectedAssessment.current_tools?.length ?? 0) > 0) {
      factors.push({
        title: "API & Middleware Integrations",
        desc: `Middleware data synchronization with ${selectedAssessment.current_tools.slice(0, 3).join(", ") || "legacy datastores"}.`
      });
    }
    if ((selectedAssessment.use_cases?.length ?? 0) > 0) {
      factors.push({
        title: `${selectedAssessment.use_cases.length} AI Use Case Target(s)`,
        desc: "Requires parsing workflows, prompt templates, and semantic embeddings for the opportunity maps."
      });
    }
    factors.push({
      title: "Human Approval Flow",
      desc: "Enforces consultant gating to validate model classification outputs prior to client-ready generation."
    });
    factors.push({
      title: "Strategy Asset Exports",
      desc: "Requires CSS-rich PDF scorecard compilation, PPTX deck exports, and DOCX pilot proposals."
    });

    return factors;
  };

  const getDeliveryTeam = (model: string) => {
    if (model === "AI Readiness Sprint") {
      return [
        { role: "AI Engagement Lead", task: "Directs workshop sprints, shapes business strategy alignment, and handles client advisory loops.", load: "100%" },
        { role: "AI Solution Architect", task: "Designs target state blueprints, maps data ingest topologies, and assesses API boundaries.", load: "50%" },
        { role: "Business Analyst", task: "Documents process bottlenecks, maps manual cycle times, and catalogs user stories.", load: "100%" },
        { role: "Document Analyst", task: "Audits corporate playbooks, identifies data silos, and classifies unstructured files.", load: "50%" }
      ];
    } else if (model === "Production Rollout") {
      return [
        { role: "AI Delivery Architect", task: "Defines scalable enterprise infrastructure, multi-agent orchestrations, and secure vector nodes.", load: "100%" },
        { role: "Project Manager", task: "Orchestrates agile deployment tracks, handles release alignment, and manages SLA gates.", load: "100%" },
        { role: "DevOps & Cloud Engineer", task: "Configures secure VPC, deployment pipelines, key vaults, and automatic failovers.", load: "70%" },
        { role: "Data Engineer", task: "Builds production ETL connections, database triggers, and delta-lake sync pipelines.", load: "80%" },
        { role: "Full-Stack Team (x2)", task: "Develops the client dashboard UI, review screens, and backend orchestration microservices.", load: "100%" },
        { role: "Change Management Lead", task: "Executes consultant training programs, tracks adoption KPIs, and writes user SOP manuals.", load: "60%" }
      ];
    } else if (model === "Managed AI Governance Retainer") {
      return [
        { role: "AI Compliance Officer", task: "Monitors bias signals, reviews GDPR logs, and handles model validation audits.", load: "100%" },
        { role: "AI Architect", task: "Implements model drift triggers, validates guardrail regex controls, and evaluates LLM runs.", load: "30%" },
        { role: "QA Engineer", task: "Maintains golden testing datasets, validates regression test metrics, and reviews logs.", load: "50%" }
      ];
    } else if (model === "AI Enablement + Training Program") {
      return [
        { role: "AI Transformation Facilitator", task: "Curates organizational enablement blueprints, runs training academies, and tracks adoption.", load: "100%" },
        { role: "Solution Architect", task: "Assists business leaders in scoping custom sandbox scripts and prompt frameworks.", load: "40%" },
        { role: "BA / Content Specialist", task: "Adapts technical training assets to match business user terminology and playbooks.", load: "100%" }
      ];
    } else {
      // Default: Pilot MVP Build
      return [
        { role: "AI Product Lead", task: "Owns MVP feature prioritization, aligns delivery checkpoints, and shapes pilot scopes.", load: "100%" },
        { role: "LLM / RAG Engineer", task: "Configures parsing scripts, creates embedding vectors, and constructs orchestration nodes.", load: "100%" },
        { role: "Full-Stack Engineer", task: "Develops responsive client-facing review dashboard screens and mounts API routes.", load: "100%" },
        { role: "QA / Evaluation Specialist", task: "Measures model hallucination rates, writes evaluation checks, and audits datasets.", load: "50%" },
        { role: "Security & Trust Auditor", task: "Reviews sanitization gates, GDPR/PII scrubbers, and SOC2 access compliance.", load: "30%" }
      ];
    }
  };

  // --- RENDERS ---
  if (!isLoggedIn) {
    return (
      <main className="min-height-screen flex flex-col items-center justify-center p-4 relative">
        {/* Glow Spheres */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-blue-600/10 blur-3xl animate-pulse-glow" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-indigo-600/10 blur-3xl animate-pulse-glow" style={{ animationDelay: "2s" }} />
        
        <div className="w-full max-w-md glass-panel p-8 rounded-2xl relative z-10">
          <div className="text-center mb-8">
            <div className="flex justify-center items-center gap-2 mb-2">
              <Brain className="w-8 h-8 text-blue-500 glow-subtle" />
              <span className="text-2xl font-bold tracking-tight text-gradient">AI Readiness Studio</span>
            </div>
            <h1 className="text-xl font-bold">AI Readiness Intelligence Studio</h1>
            <p className="text-xs text-slate-400 mt-2">
              “From business documents to AI opportunity roadmap in minutes.”
            </p>
          </div>

          <form id="login-form" onSubmit={handleLogin} className="space-y-4">
            {authError && (
              <div className="p-3 bg-red-950/50 border border-red-500/30 rounded-lg text-xs text-red-400 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}
            <div>
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-400 mb-1">Email Address</label>
              <input 
                id="login-email"
                type="email" 
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                placeholder="consultant@studio.com"
              />
            </div>
            <div>
              <label htmlFor="login-password" className="block text-xs font-semibold text-slate-400 mb-1">Password</label>
              <input 
                id="login-password"
                type="password" 
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                placeholder="••••••••"
              />
            </div>

            <button 
              type="submit" 
              className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 text-sm font-semibold transition-colors flex items-center justify-center gap-2"
            >
              <span>Access Intelligence Console</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="relative my-6 text-center">
            <span className="text-xs text-slate-500 bg-slate-950 px-2 relative z-10">WALKTHROUGH WORKSPACE</span>
            <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-slate-800" />
          </div>

          <button 
            onClick={handleDemoAccess}
            className="w-full bg-indigo-950/40 hover:bg-indigo-900/60 border border-indigo-500/30 text-indigo-300 rounded-lg py-2.5 text-xs font-semibold transition-all flex items-center justify-center gap-2"
          >
            <Sparkles className="w-4 h-4 text-indigo-400 animate-pulse" />
            <span>Load Sample Client Workspace</span>
          </button>
        </div>
      </main>
    );
  }

  return (
    <div className="min-height-screen flex flex-col relative bg-[#030712]">
      {/* Background glow layers */}
      <div className="absolute top-0 left-1/4 w-[400px] h-[400px] rounded-full bg-blue-600/5 blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-1/4 w-[400px] h-[400px] rounded-full bg-indigo-600/5 blur-3xl pointer-events-none" />

      {/* HEADER */}
      <header className="w-full glass-panel border-b border-white/5 py-4 px-6 sticky top-0 z-50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/10 rounded-lg border border-blue-500/20">
            <Brain className="w-6 h-6 text-blue-500 glow-subtle" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-gradient">AI Readiness Studio</span>
              <span className="bg-emerald-950/60 border border-emerald-500/20 text-emerald-400 text-[10px] px-2 py-0.5 rounded-full font-medium">LangGraph Engine active</span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">
              “From business documents to AI opportunity roadmap in minutes.”
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {selectedAssessment && (
            <div className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="font-semibold text-slate-300">{selectedAssessment.company_name}</span>
            </div>
          )}
          <WorkspaceSelector
            workspaces={workspaces}
            selectedId={selectedWorkspace?.id ?? null}
            onSelect={(ws) => setSelectedWorkspace(ws)}
          />
          <button 
            onClick={handleLogout}
            className="p-2 bg-slate-950 hover:bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition-colors flex items-center gap-2 text-xs"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Exit Console</span>
          </button>
        </div>
      </header>

      {/* WORKSPACE CONTENT */}
      <div className="flex-1 flex flex-col max-w-7xl w-full mx-auto p-6 relative z-10 gap-6">
        
        {/* TABS SELECTOR */}
        <div className="flex items-center justify-between bg-slate-950/60 border border-slate-800/80 p-1.5 rounded-xl">
          <div className="flex gap-2">
            <button 
              onClick={() => setActiveTab("dashboard")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${activeTab === "dashboard" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
            >
              {selectedWorkspace?.workspace_type === "enterprise" ? "Enterprise Console" : "Agency Console"}
            </button>
            <button 
              onClick={() => setActiveTab("members")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${activeTab === "members" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
            >
              Members & Access
            </button>
            <button 
              onClick={() => setActiveTab("intake")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${activeTab === "intake" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
            >
              Intake Screen
            </button>
            <button 
              onClick={() => {
                if (selectedAssessment) setActiveTab("upload");
                else alert("Create or load an assessment first!");
              }}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${activeTab === "upload" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
            >
              Document Upload
            </button>
            <button 
              onClick={() => {
                if (selectedAssessment && selectedAssessment.status === "completed") {
                  setActiveTab("insights");
                } else {
                  alert("Upload documents and run AI analysis first!");
                }
              }}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${activeTab === "insights" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
            >
              Opportunity Roadmap Hub
            </button>
          </div>
          
          <button 
            onClick={loadAssessments}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-semibold text-slate-300 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload Assessments</span>
          </button>
        </div>

        {/* 1. LANDING DASHBOARD */}
        {activeTab === "dashboard" && (
          <div className="space-y-6">
            {selectedWorkspace?.workspace_type === "enterprise" ? (
              <EnterprisePortfolio
                items={portfolioItems}
                businessUnitFilter={businessUnitFilter}
                onBusinessUnitFilter={setBusinessUnitFilter}
                onOpenAssessment={async (id) => {
                  const ass = assessments.find((a) => a.id === id);
                  if (ass) {
                    setSelectedAssessment(ass);
                    setActiveTab("insights");
                    setInsightsSubTab("investment");
                  } else {
                    const res = await fetch(`${API_BASE}/assessments/${id}`, { headers: getAuthHeaders() });
                    if (res.ok) {
                      const loaded = await res.json();
                      setSelectedAssessment(loaded);
                      setAssessments((cur) => [loaded, ...cur.filter((a) => a.id !== loaded.id)]);
                      setActiveTab("insights");
                      setInsightsSubTab("investment");
                    }
                  }
                }}
              />
            ) : (
              <AgencyEngagements
                engagements={engagementItems}
                onOpenClient={(clientId) => {
                  setSelectedClientId(String(clientId));
                  setActiveTab("intake");
                }}
                onCreateEngagement={() => setActiveTab("intake")}
              />
            )}
            {/* Executive Command Center */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass-panel p-4 rounded-xl text-center flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Overall AI Readiness</span>
                <span className="text-3xl font-extrabold text-blue-500 my-2">{overallScore > 0 ? `${overallScore}/100` : "TBD"}</span>
                <span className="text-[9px] text-slate-500">Target index for scaling</span>
              </div>
              <div className="glass-panel p-4 rounded-xl text-center flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">High-Value AI Opportunities</span>
                <span className="text-3xl font-extrabold text-indigo-400 my-2">{highValueOpportunities}</span>
                <span className="text-[9px] text-slate-500">Strategic maps created</span>
              </div>
              <div className="glass-panel p-4 rounded-xl text-center flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Quick-Win Pilots</span>
                <span className="text-3xl font-extrabold text-emerald-400 my-2">{quickWinPilots}</span>
                <span className="text-[9px] text-slate-500">Low-complexity, high-value</span>
              </div>
              <div className="glass-panel p-4 rounded-xl text-center flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Governance Risks</span>
                <span className="text-3xl font-extrabold text-amber-500 my-2">{governanceRisksCount}</span>
                <span className="text-[9px] text-slate-500">Open risk checkpoints</span>
              </div>
              <div className="glass-panel p-4 rounded-xl text-center flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Automation Potential</span>
                <span className="text-3xl font-extrabold text-purple-400 my-2">{automationPotentialVal}%</span>
                <span className="text-[9px] text-slate-500">Estimated cycles optimized</span>
              </div>
              <div className="glass-panel p-4 rounded-xl text-center flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Recommended First Pilot</span>
                <span className="text-xs font-bold text-blue-400 my-4 line-clamp-2 leading-tight">
                  {recommendedFirstPilotName}
                </span>
                <span className="text-[9px] text-slate-500">Immediate impact vector</span>
              </div>
              <div className="glass-panel p-4 rounded-xl text-center flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Risk Level</span>
                <span className="text-3xl font-extrabold text-red-400 my-2">{riskLevelVal}</span>
                <span className="text-[9px] text-slate-500">Advisory risk profile</span>
              </div>
              <div className="glass-panel p-4 rounded-xl text-center flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Approval Status</span>
                <span className={`text-xs font-bold my-4 uppercase px-2.5 py-1 rounded-full border mx-auto w-fit ${getApprovalStatusBadge(currentApprovalStatusVal)}`}>
                  {currentApprovalStatusVal}
                </span>
                <span className="text-[9px] text-slate-500">Human review flow</span>
              </div>
            </div>

            {/* Assessment listing & intake launcher */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              <div className="lg:col-span-2 glass-panel p-6 rounded-2xl flex flex-col justify-between min-h-[320px]">
                <div>
                  <h2 className="text-lg font-bold flex items-center gap-2">
                    <FileText className="w-5 h-5 text-blue-500" />
                    <span>Client Workspaces</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1 mb-4">
                    Active client folders with linked discovery assessments and roadmap outputs.
                  </p>
                  
                  {loading ? (
                    <div className="flex justify-center py-12">
                      <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
                    </div>
                  ) : clientWorkspaceGroups.length === 0 ? (
                    <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl">
                      <Sparkles className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                      <p className="text-xs text-slate-400">No active client workspaces. Start a new discovery session!</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {clientWorkspaceGroups.map((group) => (
                        <div key={group.client?.id ?? "unassigned"} className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
                          <div className="mb-3 flex items-center justify-between gap-3">
                            <div>
                              <div className="text-sm font-bold text-slate-200">
                                {group.client?.name ?? "Unassigned Assessments"}
                              </div>
                              <div className="mt-1 text-[10px] text-slate-400">
                                {group.client ? `${group.client.industry ?? "Industry pending"} • ${group.assessments.length} workspace(s)` : `${group.assessments.length} workspace(s) awaiting client mapping`}
                              </div>
                            </div>
                            {group.client && (
                              <span className="rounded-full border border-blue-500/20 bg-blue-950/30 px-2 py-1 text-[9px] font-bold uppercase text-blue-300">
                                Client Record
                              </span>
                            )}
                          </div>

                          <div className="space-y-3">
                            {group.assessments.map((ass) => (
                              <div 
                                key={ass.id}
                                onClick={() => {
                                  setSelectedAssessment(ass);
                                  if (ass.status === "completed") {
                                    setActiveTab("insights");
                                    setInsightsSubTab("summary");
                                  } else if (ass.status === "intake") {
                                    setActiveTab("upload");
                                  }
                                }}
                                className={`p-4 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-4 ${selectedAssessment?.id === ass.id ? "bg-blue-950/20 border-blue-500/40" : "bg-slate-900/40 border-slate-800 hover:border-slate-700"}`}
                              >
                                <div className="min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm font-bold text-slate-200">{ass.company_name}</span>
                                    <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase ${ass.status === "completed" ? "bg-emerald-950 text-emerald-400 border border-emerald-500/20" : "bg-blue-950 text-blue-400 border border-blue-500/20"}`}>
                                      {ass.status}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-3 text-[10px] text-slate-400 mt-1">
                                    <span>Industry: {ass.industry}</span>
                                    <span>•</span>
                                    <span>Size: {ass.company_size}</span>
                                    {ass.overall_score > 0 && (
                                      <>
                                        <span>•</span>
                                        <span className="text-blue-400 font-bold">Overall Score: {int(ass.overall_score)}/100</span>
                                      </>
                                    )}
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 shrink-0">
                                  <button
                                    type="button"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      handleDeleteAssessment(ass.id);
                                    }}
                                    className="rounded-lg border border-red-500/20 bg-red-950/20 p-2 text-red-400 hover:bg-red-950/40"
                                    title="Delete assessment"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                  <ArrowRight className="w-4 h-4 text-slate-500" />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                  <span>{clients.length} client record(s) • {assessments.length} assessment workspace(s)</span>
                  <button 
                    onClick={() => setActiveTab("intake")}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>New Assessment</span>
                  </button>
                </div>
              </div>

              {/* Status / Quick Actions */}
              <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
                <div>
                  <h3 className="font-bold text-sm text-slate-300 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">Active Target Summary</h3>
                  
                  {selectedAssessment ? (
                    <div className="space-y-4 text-xs">
                      <div>
                        <span className="text-slate-400 block mb-0.5">Focus Company:</span>
                        <span className="font-bold text-slate-200">{selectedAssessment.client?.name ?? selectedAssessment.company_name}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block mb-0.5">Compliance Needs:</span>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {selectedAssessment.compliance_requirements?.map((c: string) => (
                            <span key={c} className="bg-slate-900 border border-slate-800 text-[10px] text-slate-300 px-2 py-0.5 rounded">
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <span className="text-slate-400 block mb-0.5">Cloud Preference:</span>
                        <span className="font-semibold text-blue-400">{selectedAssessment.cloud_preference}</span>
                      </div>
                      {selectedAssessment.recommended_first_pilot && (
                        <div>
                          <span className="text-slate-400 block mb-0.5">Recommended First Pilot:</span>
                          <span className="font-bold text-indigo-400 block">{selectedAssessment.recommended_first_pilot}</span>
                          <span className="text-[10px] text-slate-400 mt-1 block">{selectedAssessment.expected_pilot_impact}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-xs text-slate-500">
                      Select or create an assessment from the dashboard table.
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-slate-800/80">
                  <button 
                    onClick={() => {
                      if (selectedAssessment) {
                        setActiveTab("insights");
                        setInsightsSubTab("export");
                      } else {
                        alert("Select an assessment first!");
                      }
                    }}
                    className="w-full bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Strategic Outputs</span>
                  </button>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* 2. CLIENT INTAKE SCREEN */}
        {activeTab === "members" && selectedWorkspace && (
          <MemberAccessPanel
            members={workspaceMembers}
            clients={clients.map((c) => ({ id: c.id, name: c.name }))}
            canManage={["owner_admin"].includes(selectedWorkspace.role || "")}
            busy={memberBusy}
            message={memberMessage}
            onRefresh={() => loadWorkspaceMembers(selectedWorkspace.id)}
            onAddMember={handleAddWorkspaceMember}
            onUpdateMember={handleUpdateWorkspaceMember}
          />
        )}

        {activeTab === "intake" && (
          <div className="glass-panel p-8 rounded-2xl max-w-3xl mx-auto relative">
            {/* Demo autofill floating overlay */}
            <div className="absolute top-6 right-8">
              <button 
                type="button"
                onClick={handleIntakeAutoFill}
                className="bg-indigo-950/60 hover:bg-indigo-900/60 border border-indigo-500/30 text-indigo-300 px-3 py-1.5 rounded-lg text-[10px] font-bold tracking-tight transition-all flex items-center gap-1.5 animate-bounce"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span>Auto-Fill Mock B2B Data</span>
              </button>
            </div>

            <div className="mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Brain className="w-6 h-6 text-blue-500" />
                <span>AI Transformation Discovery Intake</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Establish corporate structure, technology alignments, pain points, and strategic AI goals.
              </p>
            </div>

            <form onSubmit={handleIntakeSubmit} className="space-y-6">
              <div>
                <label htmlFor="client-workspace" className="block text-xs font-semibold text-slate-400 mb-1.5">Client Workspace</label>
                <select
                  id="client-workspace"
                  value={selectedClientId}
                  onChange={e => {
                    const value = e.target.value;
                    setSelectedClientId(value);
                    const client = clients.find((item) => item.id === parseInt(value, 10));
                    if (client) {
                      setCompanyName(client.name);
                      setIndustry(client.industry || "Professional Services");
                      setCompanySize(client.company_size || "100-500 employees");
                      setCloudPref(client.cloud_preference || "Cloud-agnostic");
                      setCompliance(client.compliance_requirements || []);
                    }
                  }}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                >
                  <option value="">Create a new client from this intake</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-[10px] text-slate-500">
                  Reuse an existing client workspace or leave this on new to create one automatically.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="company-name" className="block text-xs font-semibold text-slate-400 mb-1.5">Company Legal Name</label>
                  <input 
                    id="company-name"
                    type="text" 
                    value={companyName}
                    onChange={e => setCompanyName(e.target.value)}
                    required
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                    disabled={selectedClient !== null}
                    placeholder="Apex Global Partners Inc."
                  />
                </div>
                <div>
                  <label htmlFor="industry-vertical" className="block text-xs font-semibold text-slate-400 mb-1.5">Industry Vertical</label>
                  <select 
                    id="industry-vertical"
                    value={industry}
                    onChange={e => setIndustry(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                    disabled={selectedClient !== null}
                  >
                    <option>Professional Services</option>
                    <option>Financial Technology</option>
                    <option>Healthcare & Pharma</option>
                    <option>Logistics & Supply Chain</option>
                    <option>Retail & E-Commerce</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="company-size" className="block text-xs font-semibold text-slate-400 mb-1.5">Company Headcount Scale</label>
                  <select 
                    id="company-size"
                    value={companySize}
                    onChange={e => setCompanySize(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                    disabled={selectedClient !== null}
                  >
                    <option>1-50 employees</option>
                    <option>50-100 employees</option>
                    <option>100-500 employees</option>
                    <option>500-1000 employees</option>
                    <option>1000+ employees</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="cloud-preference" className="block text-xs font-semibold text-slate-400 mb-1.5">Cloud Hosting Preference</label>
                  <select 
                    id="cloud-preference"
                    value={cloudPref}
                    onChange={e => setCloudPref(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                    disabled={selectedClient !== null}
                  >
                    <option>Azure</option>
                    <option>AWS</option>
                    <option>Google Cloud Platform</option>
                    <option>Cloud-agnostic</option>
                  </select>
                </div>
              </div>

              {/* Multi Select Arrays */}
              <div>
                <span className="block text-xs font-semibold text-slate-400 mb-2">Target Departments in Scope</span>
                <div className="flex flex-wrap gap-2">
                  {["Operations", "Customer Support", "Sales & Pre-sales", "Compliance & Governance", "HR & Training"].map(dept => {
                    const active = departments.includes(dept);
                    return (
                      <button 
                        type="button"
                        key={dept}
                        onClick={() => toggleSelection(dept, departments, setDepartments)}
                        className={`text-[10px] px-3 py-1.5 rounded-lg border font-semibold transition-all ${active ? "bg-blue-600/20 border-blue-500 text-blue-300" : "bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700"}`}
                      >
                        {dept}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <span className="block text-xs font-semibold text-slate-400 mb-2">Current Tooling Stack</span>
                <div className="flex flex-wrap gap-2">
                  {["Salesforce", "HubSpot", "Microsoft Excel", "SharePoint", "Jira Service Desk", "Slack", "Zendesk", "SAP"].map(tool => {
                    const active = tools.includes(tool);
                    return (
                      <button
                        type="button"
                        key={tool}
                        onClick={() => toggleSelection(tool, tools, setTools)}
                        className={`text-[10px] px-3 py-1.5 rounded-lg border font-semibold transition-all ${active ? "bg-blue-600/20 border-blue-500 text-blue-300" : "bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700"}`}
                      >
                        {tool}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <span className="block text-xs font-semibold text-slate-400 mb-2">Core Compliance Requirements</span>
                <div className="flex flex-wrap gap-2">
                  {["GDPR", "HIPAA", "SOC2 Type II", "PCI-DSS", "ISO 27001"].map(comp => {
                    const active = compliance.includes(comp);
                    return (
                      <button 
                        type="button"
                        key={comp}
                        onClick={() => toggleSelection(comp, compliance, setCompliance)}
                        className={`text-[10px] px-3 py-1.5 rounded-lg border font-semibold transition-all ${active ? "bg-blue-600/20 border-blue-500 text-blue-300" : "bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700"}`}
                      >
                        {comp}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Cards Grid pain points */}
              <div>
                <span className="block text-xs font-semibold text-slate-400 mb-2">Primary Workflow Pain Points (Multi-Select Cards)</span>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    "Manual Process Overload", 
                    "Data Silos", 
                    "Slow Support Response Times",
                    "High Operational Costs",
                    "Compliance Audit Stress",
                    "Customer Churn Gaps"
                  ].map(pain => {
                    const active = painPoints.includes(pain);
                    return (
                      <div 
                        key={pain}
                        onClick={() => toggleSelection(pain, painPoints, setPainPoints)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all text-center flex flex-col justify-center items-center h-20 ${active ? "bg-blue-600/10 border-blue-500 text-blue-300" : "bg-slate-900/30 border-slate-800 text-slate-400 hover:border-slate-700"}`}
                      >
                        <span className="text-[10px] font-bold tracking-tight leading-tight">{pain}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <span className="block text-xs font-semibold text-slate-400 mb-2">Transformation AI Goals (Multi-Select Cards)</span>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    "Efficiency / Cost Reduction", 
                    "Enhanced Customer Experience", 
                    "Strategic Product Scaling",
                    "Data-Driven Decisions",
                    "Governance Readiness",
                    "Legacy Tech Modernization"
                  ].map(goal => {
                    const active = aiGoals.includes(goal);
                    return (
                      <div 
                        key={goal}
                        onClick={() => toggleSelection(goal, aiGoals, setAiGoals)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all text-center flex flex-col justify-center items-center h-20 ${active ? "bg-blue-600/10 border-blue-500 text-blue-300" : "bg-slate-900/30 border-slate-800 text-slate-400 hover:border-slate-700"}`}
                      >
                        <span className="text-[10px] font-bold tracking-tight leading-tight">{goal}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <label htmlFor="strategic-objectives" className="block text-xs font-semibold text-slate-400 mb-1.5">Free-Text Strategic Objectives</label>
                <textarea 
                  id="strategic-objectives"
                  value={goalsText}
                  onChange={e => setGoalsText(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                  placeholder="e.g. Accelerate client delivery margins and audit GDPR supply agreements securely."
                />
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[10px] text-slate-500">Step 1 of 3: Core Profile Completed</span>
                <button 
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg text-xs font-bold transition-colors flex items-center gap-1.5"
                >
                  <span>Continue to Document Upload</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          </div>
        )}

        {/* 3. DOCUMENT UPLOAD SCREEN */}
        {activeTab === "upload" && selectedAssessment && (
          <div className="max-w-2xl mx-auto space-y-6">
            
            <div className="glass-panel p-8 rounded-2xl relative text-center">
              <h2 className="text-lg font-bold mb-1">Audit Documentation Workspace</h2>
              <p className="text-xs text-slate-400 mb-6">
                Upload operational playbooks, SOP sheets, or audit files to feed the Multi-Agent scoring analyzer.
              </p>

              {/* Drag Drop Box */}
              <div className="border border-dashed border-slate-700 hover:border-blue-500/60 rounded-xl p-8 bg-slate-900/20 cursor-pointer transition-all flex flex-col items-center">
                <UploadCloud className="w-12 h-12 text-slate-500 mb-2" />
                <span className="text-xs font-bold text-slate-300">Drag SOP and Support Logs files here</span>
                <span className="text-[10px] text-slate-500 mt-1">Accepts PDF, DOCX, TXT (Maximum size 12MB)</span>
                <input 
                  type="file" 
                  multiple 
                  accept=".pdf,.docx,.txt"
                  onChange={e => {
                    if (e.target.files) {
                      setSelectedFiles(Array.from(e.target.files));
                    }
                  }}
                  className="hidden" 
                  id="file-picker" 
                />
                <button 
                  onClick={() => document.getElementById("file-picker")?.click()}
                  className="mt-4 bg-slate-900 hover:bg-slate-800 border border-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-colors text-slate-300"
                >
                  Browse Files
                </button>
              </div>

              {selectedFiles.length > 0 && (
                <div className="mt-4 bg-slate-950 p-3 rounded-lg border border-slate-800 text-left text-xs max-h-32 overflow-y-auto space-y-2">
                  <span className="font-bold text-slate-400">Selected Files:</span>
                  {selectedFiles.map(file => (
                    <div key={file.name} className="flex items-center justify-between text-slate-300">
                      <span className="truncate">{file.name}</span>
                      <span className="text-[10px] text-slate-500">{(file.size / 1024).toFixed(1)} KB</span>
                    </div>
                  ))}
                </div>
              )}

              {selectedFiles.length === 0 && (
                <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-950/10 p-3 text-left text-xs text-amber-200">
                  No files selected yet. Running the pipeline now will use a synthetic briefing file built from this intake so the analysis stays grounded to the client context.
                </div>
              )}

              {/* Launch Pipeline trigger */}
              <div className="mt-8 flex items-center justify-between pt-4 border-t border-slate-800">
                <button 
                  onClick={() => {
                    setSelectedFiles([]);
                    setSelectedAssessment(null);
                    setActiveTab("dashboard");
                  }}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleFileUploadAndRun}
                  disabled={isProcessing}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white px-6 py-2.5 rounded-lg text-xs font-bold transition-colors flex items-center gap-2"
                >
                  <Brain className="w-4 h-4" />
                  <span>Execute LangGraph AI Pipeline</span>
                </button>
              </div>
            </div>

            {/* PROCESSING POPUP / ANIMATION */}
            {isProcessing && (
              <div className="glass-panel p-6 rounded-2xl border border-blue-500/30 bg-slate-950/80 shadow-2xl relative overflow-hidden">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
                    <span className="text-sm font-bold text-slate-200">Executing Multi-Agent Graphs...</span>
                  </div>
                  <span className="text-xs font-bold text-blue-400">{uploadProgress}%</span>
                </div>
                
                {/* Progress bar */}
                <div className="w-full bg-slate-900 h-2 rounded-full mb-6 overflow-hidden border border-slate-800">
                  <div className="bg-gradient-to-r from-blue-600 to-indigo-500 h-full rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
                </div>

                {/* Vertical processing nodes lists */}
                  <div className="space-y-3 relative z-10 pl-6 border-l border-slate-800">
                  {steps.map((step, idx) => {
                    const active = idx === processingStep;
                    const completed = idx < processingStep;
                    return (
                      <div key={step} className="flex items-center gap-3 relative">
                        {/* Dot indicator */}
                        <div className={`absolute -left-[30px] w-4 h-4 rounded-full border flex items-center justify-center text-[8px] font-bold ${completed ? "bg-emerald-950 border-emerald-500 text-emerald-400" : active ? "bg-blue-600 border-blue-500 text-white animate-pulse" : "bg-slate-950 border-slate-800 text-slate-600"}`}>
                          {completed ? "✓" : idx + 1}
                        </div>
                        <span className={`text-xs font-semibold ${active ? "text-blue-400" : completed ? "text-slate-400" : "text-slate-600"}`}>
                          {step}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            
            {/* Extracted Signals Display table */}
            {selectedAssessment.extracted_signals && selectedAssessment.extracted_signals.length > 0 && (
              <div className="glass-panel p-6 rounded-2xl">
                <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">Extracted Business Signals</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-bold">
                        <th className="pb-2">Source File</th>
                        <th className="pb-2">Signal Type</th>
                        <th className="pb-2">Confidence</th>
                        <th className="pb-2">Parsed Finding</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {selectedAssessment.extracted_signals.map((sig, idx: number) => (
                        <tr key={idx} className="text-slate-300">
                          <td className="py-2.5 truncate max-w-[120px] font-semibold">{sig.source_file}</td>
                          <td className="py-2.5">{sig.signal_type}</td>
                          <td className="py-2.5 text-blue-400 font-bold">{(sig as { evidence_tier?: string }).evidence_tier || "uncalibrated"}</td>
                          <td className="py-2.5 text-slate-400">{sig.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

          </div>
        )}

        {/* 4. ASSESSMENT INSIGHTS HUB (11-STEP DETAILS) */}
        {activeTab === "insights" && selectedAssessment && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            
            {/* Sub-tab sidebar */}
            <div className="glass-panel p-4 rounded-2xl flex flex-col gap-1.5 h-fit">
              <div className="px-2 py-3 border-b border-slate-800 mb-2">
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Transformation Report</span>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs font-bold text-slate-300 truncate max-w-[100px]">{selectedAssessment.company_name}</span>
                  <span className="text-[10px] text-blue-400 font-extrabold">{int(selectedAssessment.overall_score)}/100</span>
                </div>
              </div>

              {[
                { id: "summary", label: "Executive Summary", icon: FileText },
                { id: "evidence", label: "Evidence Trail", icon: Sparkles },
                { id: "bottlenecks", label: "Process Bottlenecks", icon: Trash2 },
                { id: "opportunity", label: "Opportunities Map", icon: Brain },
                { id: "matrix", label: "Prioritization Grid", icon: BarChart3 },
                { id: "scoring", label: "Readiness Scores", icon: TrendingUp },
                { id: "risks", label: "Risk & Governance", icon: Shield },
                { id: "pilot", label: "Recommended Pilot", icon: Sparkles },
                { id: "roadmap", label: "90-Day Roadmap", icon: Calendar },
                { id: "commercial", label: "Commercial Strategy", icon: Coins },
                { id: "investment", label: "Investment Intelligence", icon: TrendingUp },
                { id: "export", label: "Strategy Asset Generator", icon: Download },
                { id: "proposal", label: "Proposal / SOW", icon: FileText },
                { id: "workflow", label: "Review Workflow", icon: CheckCircle }
              ].map(sub => {
                const active = insightsSubTab === sub.id;
                const Icon = sub.icon;
                return (
                  <button 
                    key={sub.id}
                    onClick={() => setInsightsSubTab(sub.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-left transition-all ${active ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900"}`}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{sub.label}</span>
                  </button>
                );
              })}

              <div className="mt-4 pt-4 border-t border-slate-800 space-y-2">
                {/* Human Review Mode Toggle */}
                <label className="flex cursor-pointer items-center justify-between p-2 bg-slate-950 rounded-lg border border-slate-800">
                  <div className="flex items-center gap-1.5">
                    <Edit3 className="w-3.5 h-3.5 text-blue-400" />
                    <span className="text-[10px] font-bold text-slate-300">Human Review Mode</span>
                  </div>
                  <input 
                    type="checkbox"
                    checked={isReviewMode}
                    onChange={e => setIsReviewMode(e.target.checked)}
                    className="w-3.5 h-3.5 accent-blue-500 cursor-pointer"
                  />
                </label>

                {isReviewMode && (
                  <button 
                    onClick={handleReviewSave}
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg py-1.5 text-[10px] font-bold transition-colors flex items-center justify-center gap-1"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>Save Manual Edits</span>
                  </button>
                )}
              </div>
            </div>

            {/* Sub-tab body area */}
            <div className="lg:col-span-3 space-y-6">
              
              {/* Executive summary block at the top of every assessment */}
              <div className="glass-panel p-5 rounded-2xl bg-gradient-to-r from-blue-950/20 to-indigo-950/20 border-blue-500/20 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 blur-xl rounded-full" />
                <div className="flex items-center gap-1.5 mb-2">
                  <Sparkles className="w-4 h-4 text-blue-400 glow-subtle" />
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Executive Briefing Card</span>
                  <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase ${isDocumentGrounded ? "border-emerald-500/20 bg-emerald-950/20 text-emerald-300" : "border-indigo-500/20 bg-indigo-950/20 text-indigo-300"}`}>
                    {isDocumentGrounded ? "Document-Grounded Evidence" : "Structured Brief Evidence"}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase ${getApprovalStatusBadge(approvalStatus)}`}>
                    {approvalStatus}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-slate-100">{selectedAssessment.company_name} AI Opportunity Report</h3>
                <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                  {selectedAssessment.client_summary || selectedAssessment.business_summary || "No business summary computed yet."}
                </p>
                <div className="flex items-center gap-4 mt-3 pt-3 border-t border-slate-800 text-[10px] text-slate-400">
                  <span>Confidence: <strong className="text-amber-300">Uncalibrated estimate</strong></span>
                  <span>•</span>
                  <span>Analysis: <strong className="text-indigo-400">{selectedAssessment.analysis_mode || "real"} / {selectedAssessment.model_run_status || "n/a"}</strong></span>
                  <span>•</span>
                  <span>Readiness Rank: <strong className="text-emerald-400">{int(selectedAssessment.overall_score)}/100</strong> <span className="text-slate-500">(deterministic weighted)</span></span>
                </div>
              </div>

              {/* SUB-TABS VIEWS RENDERING */}
              
              {/* A: Executive Summary View */}
              {insightsSubTab === "summary" && (
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  {!isDocumentGrounded && (
                    <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4 text-xs text-amber-200">
                      This run used a synthetic briefing file generated from the intake rather than uploaded source documents. The outputs are client-specific, but they should still be validated against real artifacts before external sharing.
                    </div>
                  )}

                  <h3 className="text-base font-bold">Transformation Context</h3>

                  <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <span className="text-slate-400 text-xs block mb-1">Client-facing summary</span>
                        <p className="text-[11px] text-slate-500">Use this as the polished external narrative that appears in exports.</p>
                      </div>
                      <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase ${getApprovalStatusBadge(approvalStatus)}`}>
                        {approvalStatus}
                      </span>
                    </div>

                    {isReviewMode ? (
                      <textarea
                        value={selectedAssessment.client_summary || ""}
                        onChange={(e) => setSelectedAssessment({ ...selectedAssessment, client_summary: e.target.value })}
                        className="min-h-[120px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:outline-none"
                        placeholder="Write the polished client-facing summary that should appear in exports."
                      />
                    ) : (
                      <p className="text-xs leading-relaxed text-slate-200">
                        {selectedAssessment.client_summary || selectedAssessment.business_summary || "No client-facing summary prepared yet."}
                      </p>
                    )}

                    {isReviewMode && (
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <div>
                          <label htmlFor="approval-status" className="mb-1 block text-xs text-slate-400">Review status</label>
                          <select
                            id="approval-status"
                            value={approvalStatus}
                            onChange={(e) => setSelectedAssessment({ ...selectedAssessment, approval_status: e.target.value })}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:outline-none"
                          >
                            <option value="draft">Draft</option>
                            <option value="reviewed">Reviewed</option>
                            <option value="approved">Approved</option>
                          </select>
                        </div>
                        <div>
                          <label htmlFor="reviewer-notes" className="mb-1 block text-xs text-slate-400">Internal reviewer notes</label>
                          <textarea
                            id="reviewer-notes"
                            value={selectedAssessment.reviewer_notes || ""}
                            onChange={(e) => setSelectedAssessment({ ...selectedAssessment, reviewer_notes: e.target.value })}
                            className="min-h-[84px] w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:outline-none"
                            placeholder="Internal notes for your consulting team. These are not meant to be client-facing."
                          />
                        </div>
                      </div>
                    )}

                    {!isReviewMode && selectedAssessment.reviewer_notes && (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
                        <span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-slate-500">Internal reviewer notes</span>
                        <p className="text-xs text-slate-400">{selectedAssessment.reviewer_notes}</p>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl">
                      <span className="text-slate-400 text-xs block mb-1">Main Strategic Goals</span>
                      {isReviewMode ? (
                        <textarea 
                          value={selectedAssessment.main_business_goals || ""}
                          onChange={e => setSelectedAssessment({...selectedAssessment, main_business_goals: e.target.value})}
                          className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs focus:outline-none"
                        />
                      ) : (
                        <p className="text-xs text-slate-200">{selectedAssessment.main_business_goals}</p>
                      )}
                    </div>
                    <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl flex flex-col justify-between">
                      <div>
                        <span className="text-slate-400 text-xs block mb-1">Target Departments</span>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {selectedAssessment.departments?.map((d: string) => (
                            <span key={d} className="bg-blue-950/40 border border-blue-500/20 text-blue-300 text-[9px] px-2 py-0.5 rounded-full font-semibold">
                              {d}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="mt-3">
                        <span className="text-slate-400 text-xs block mb-1">Primary Tools</span>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {selectedAssessment.current_tools?.map((t: string) => (
                            <span key={t} className="bg-slate-950 border border-slate-800 text-slate-400 text-[9px] px-2 py-0.5 rounded">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {evidenceHighlights.length > 0 && (
                    <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl">
                      <span className="text-slate-400 text-xs block mb-2">Evidence Highlights</span>
                      <div className="space-y-2">
                        {evidenceHighlights.map((signal, idx) => (
                          <div key={`${signal.source_file}-${idx}`} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                            <div className="flex items-center justify-between gap-3 text-[10px]">
                              <span className="font-bold text-slate-200">{signal.signal_type}</span>
                              <span className="text-blue-400 font-bold">{signal.confidence}% confidence</span>
                            </div>
                            <p className="mt-1 text-xs text-slate-400">{signal.description}</p>
                            <p className="mt-2 text-[10px] text-slate-500">Source: {signal.source_file}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Before vs After Section */}
                  <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                    <div>
                      <h4 className="text-xs uppercase font-extrabold tracking-wider text-indigo-400 flex items-center gap-1.5">
                        <TrendingUp className="w-4 h-4 shrink-0" />
                        <span>Business Case: Before vs After Transformation</span>
                      </h4>
                      <p className="text-[10px] text-slate-500 mt-0.5">Comparative projection of AI-enabled operational efficiencies.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[
                        {
                          workflow: "Proposal Drafting",
                          before: "2–3 days of manual copy-pasting reference sections, winning sheets, and legal schedules.",
                          after: "First draft in under 30 minutes with centralized approved knowledge reuse and automatic formatting."
                        },
                        {
                          workflow: "Support Triage",
                          before: "Manual classification, incident tagging, and engineers scanning inbox directories.",
                          after: "Autonomous ticket routing and draft responses with confidence metrics and human sign-off."
                        },
                        {
                          workflow: "Compliance Review",
                          before: "Checklist-based manual review of agreement provisions and GDPR checklists.",
                          after: "AI-assisted policy gap scanning highlighting deviations across client service contracts."
                        },
                        {
                          workflow: "Knowledge Search",
                          before: "Scattered information and team files distributed across SharePoint, Slack, and emails.",
                          after: "Source-backed conversational answer retrieval with direct document citations."
                        }
                      ].map((item, idx) => (
                        <div key={idx} className="p-3 bg-slate-950/50 border border-slate-800 rounded-lg space-y-2">
                          <span className="text-xs font-bold text-slate-200 block">{item.workflow}</span>
                          <div className="grid grid-cols-2 gap-3 text-[10px]">
                            <div className="border-r border-slate-800/80 pr-2">
                              <span className="text-red-400 font-bold uppercase tracking-wider block text-[8px] mb-1">Current State:</span>
                              <p className="text-slate-400 leading-normal">{item.before}</p>
                            </div>
                            <div>
                              <span className="text-emerald-400 font-bold uppercase tracking-wider block text-[8px] mb-1">AI-Enabled State:</span>
                              <p className="text-slate-300 leading-normal">{item.after}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Evidence Trail View */}
              {insightsSubTab === "evidence" && (
                <div className="glass-panel p-6 rounded-2xl space-y-6">
                  <div>
                    <h3 className="text-base font-bold flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-blue-500 glow-subtle" />
                      <span>Opportunity Evidence Trail</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Direct audit trails linking client context and uploaded documents to AI transformation opportunities.
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 text-xs space-y-2">
                    <span className="font-semibold text-slate-300 block">Grounding Mode:</span>
                    <p className="text-slate-400">
                      This workspace is currently backed by <strong className="text-blue-400">{isDocumentGrounded ? "Document-Grounded Evidence" : "Structured Brief Evidence"}</strong>. 
                      {isDocumentGrounded 
                        ? " All signals represent verified passages parsed from your uploaded corporate playbooks and audit files."
                        : " Signals are derived from standard professional services intake profiles and our walkthrough template brief."
                      }
                    </p>
                  </div>

                  {selectedAssessment.extracted_signals && selectedAssessment.extracted_signals.length > 0 ? (
                    <div className="space-y-4">
                      {selectedAssessment.extracted_signals.map((sig, idx: number) => (
                        <div key={idx} className="p-4 bg-slate-900/30 border border-slate-800 rounded-xl flex flex-col md:flex-row justify-between gap-4 hover:border-slate-700 transition-all">
                          <div className="space-y-1.5">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded border border-blue-500/20 bg-blue-950/20 text-blue-300">
                                {sig.signal_type}
                              </span>
                              <span className="text-[10px] text-slate-500 font-medium">
                                Source: <strong>{sig.source_file}</strong>
                              </span>
                            </div>
                            <p className="text-xs text-slate-200 leading-relaxed font-semibold">
                              {sig.description}
                            </p>
                          </div>
                          <div className="shrink-0 flex items-center">
                            <span className="text-sm font-extrabold text-emerald-400 bg-emerald-950/40 border border-emerald-500/20 px-2.5 py-1 rounded-lg">
                              {int(sig.confidence)}% Conf.
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl">
                      <Sparkles className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                      <p className="text-xs text-slate-400">No signals have been extracted yet. Select a preloaded walkthrough workspace or run the AI pipeline.</p>
                    </div>
                  )}
                </div>
              )}

              {/* B: Process Bottlenecks Tab */}
              {insightsSubTab === "bottlenecks" && (
                <div className="glass-panel p-6 rounded-2xl">
                  <h3 className="text-base font-bold mb-4">Detected Process Bottlenecks</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 font-bold">
                          <th className="pb-3">Department</th>
                          <th className="pb-3">Process Name</th>
                          <th className="pb-3">Bottleneck Description</th>
                          <th className="pb-3 text-center">AI Potential</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {selectedAssessment.bottlenecks?.map((b, idx: number) => (
                          <tr key={idx} className="text-slate-300">
                            <td className="py-3 font-semibold">{b.department}</td>
                            <td className="py-3 text-blue-400">{b.process_name}</td>
                            <td className="py-3 text-slate-400">{b.bottleneck_description}</td>
                            <td className="py-3 text-center">
                              <span className={`px-2.5 py-0.5 rounded font-bold uppercase text-[9px] ${b.ai_potential === "High" ? "bg-emerald-950 text-emerald-400" : "bg-blue-950 text-blue-400"}`}>
                                {b.ai_potential}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* C: AI Opportunity Map Tab */}
              {insightsSubTab === "opportunity" && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold">Prioritized AI Use Case Catalog</h3>
                  
                  <div className="space-y-4">
                    {selectedAssessment.use_cases?.map((u, idx: number) => (
                      <div key={idx} className="p-5 bg-slate-900/30 border border-slate-800 rounded-xl relative hover:border-slate-700 transition-all">
                        {/* Priority indicator */}
                        <div className="absolute top-4 right-4 flex items-center gap-2">
                          <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase ${u.priority === "P1" ? "bg-red-950 text-red-400 border border-red-500/20" : "bg-amber-950 text-amber-400 border border-amber-500/20"}`}>
                            {u.priority}
                          </span>
                          <span className="text-[10px] text-amber-300 font-bold">Uncalibrated estimate</span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-xs text-indigo-400 font-semibold">{u.department}</span>
                          <span className="text-slate-600 text-xs">•</span>
                          <span className="text-[10px] text-slate-400">Complexity: <strong>{u.complexity}</strong></span>
                          <span className="text-slate-600 text-xs">•</span>
                          <span className="text-[10px] text-slate-400">Value: <strong className="text-emerald-400">{u.value}</strong></span>
                        </div>

                        {isReviewMode ? (
                          <div className="space-y-3 mt-3 pt-3 border-t border-slate-800">
                            <div>
                              <label className="block text-[10px] text-slate-500 font-semibold mb-0.5">Opportunity Title</label>
                              <input 
                                type="text"
                                value={u.use_case_name || ""}
                                onChange={e => {
                                  const updated = [...selectedAssessment.use_cases];
                                  updated[idx].use_case_name = e.target.value;
                                  setSelectedAssessment({ ...selectedAssessment, use_cases: updated });
                                }}
                                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] text-slate-500 font-semibold mb-0.5">Description</label>
                              <textarea 
                                value={u.description || ""}
                                onChange={e => {
                                  const updated = [...selectedAssessment.use_cases];
                                  updated[idx].description = e.target.value;
                                  setSelectedAssessment({ ...selectedAssessment, use_cases: updated });
                                }}
                                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none h-16"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] text-slate-500 font-semibold mb-0.5">Why this was recommended (Evidence)</label>
                              <textarea 
                                value={u.evidence || ""}
                                onChange={e => {
                                  const updated = [...selectedAssessment.use_cases];
                                  updated[idx].evidence = e.target.value;
                                  setSelectedAssessment({ ...selectedAssessment, use_cases: updated });
                                }}
                                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none h-16"
                              />
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <label className="block text-[10px] text-slate-500 font-semibold mb-0.5">Value</label>
                                <select 
                                  value={u.value || "High"}
                                  onChange={e => {
                                    const updated = [...selectedAssessment.use_cases];
                                    updated[idx].value = e.target.value;
                                    setSelectedAssessment({ ...selectedAssessment, use_cases: updated });
                                  }}
                                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none"
                                >
                                  <option value="High">High</option>
                                  <option value="Medium">Medium</option>
                                  <option value="Low">Low</option>
                                </select>
                              </div>
                              <div>
                                <label className="block text-[10px] text-slate-500 font-semibold mb-0.5">Complexity</label>
                                <select 
                                  value={u.complexity || "Low"}
                                  onChange={e => {
                                    const updated = [...selectedAssessment.use_cases];
                                    updated[idx].complexity = e.target.value;
                                    setSelectedAssessment({ ...selectedAssessment, use_cases: updated });
                                  }}
                                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none"
                                >
                                  <option value="High">High</option>
                                  <option value="Medium">Medium</option>
                                  <option value="Low">Low</option>
                                </select>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <>
                            <h4 className="text-sm font-bold text-slate-200 mt-2">{u.use_case_name}</h4>
                            <p className="text-xs text-slate-400 mt-1 leading-relaxed">{u.description}</p>
                            
                            {/* Evidence reasoning callout */}
                            {u.evidence && (
                              <div className="mt-3 p-3 bg-slate-950 rounded-xl border border-slate-800 text-[10px] text-slate-400 flex flex-col gap-1.5">
                                <div className="flex items-center gap-1.5 justify-between flex-wrap">
                                  <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                                    <Sparkles className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                                    <span>Why this was recommended:</span>
                                  </span>
                                  <span className={`text-[8px] font-extrabold uppercase px-2 py-0.5 rounded border ${isDocumentGrounded ? "border-emerald-500/20 bg-emerald-950/20 text-emerald-300" : "border-indigo-500/20 bg-indigo-950/20 text-indigo-300"}`}>
                                    {isDocumentGrounded ? "Document-Grounded Evidence" : "Structured Brief Evidence"}
                                  </span>
                                </div>
                                <p className="text-xs text-slate-400 leading-relaxed">{u.evidence}</p>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* D: Prioritization Matrix 2x2 SVG Quadrant */}
              {insightsSubTab === "matrix" && (
                <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
                  <h3 className="text-base font-bold mb-1">Use Case Prioritization Matrix</h3>
                  <p className="text-xs text-slate-400 mb-6">Interactive 2x2 map charting Complexity versus Business Value.</p>
                  
                  {/* The 2x2 Grid SVG */}
                  <div className="w-full aspect-[4/3] max-w-lg mx-auto bg-slate-950 border border-slate-800 rounded-xl relative p-4 flex flex-col justify-between">
                    
                    {/* Quadrant labels */}
                    <div className="absolute top-4 left-4 text-[9px] uppercase font-bold text-emerald-400 tracking-wider bg-emerald-950/20 px-2 py-0.5 rounded border border-emerald-500/20">Strategic Bets (High Value / High Complexity)</div>
                    <div className="absolute top-4 right-4 text-[9px] uppercase font-bold text-blue-400 tracking-wider bg-blue-950/20 px-2 py-0.5 rounded border border-blue-500/20">Start Now (High Value / Low Complexity)</div>
                    <div className="absolute bottom-4 left-4 text-[9px] uppercase font-bold text-slate-500 tracking-wider bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800">Long-term (Low Value / High Complexity)</div>
                    <div className="absolute bottom-4 right-4 text-[9px] uppercase font-bold text-amber-500 tracking-wider bg-amber-950/20 px-2 py-0.5 rounded border border-amber-500/20">Incubate (Low Value / Low Complexity)</div>

                    {/* Centered crosshair lines */}
                    <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-slate-800" />
                    <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-slate-800" />
                    
                    {/* Render use cases dots */}
                    <svg className="w-full h-full relative z-10" viewBox="0 0 100 100">
                      {selectedAssessment.use_cases?.map((u, idx: number) => {
                        const { x, y } = mapMatrixCoordinates(u.value, u.complexity);
                        return (
                          <g key={idx} className="cursor-pointer group">
                            <circle 
                              cx={x} 
                              cy={y} 
                              r="3" 
                              className={`stroke-white/30 stroke-1 hover:r-4 transition-all duration-300 ${u.priority === "P1" ? "fill-blue-500" : "fill-indigo-400"}`} 
                            />
                            {/* Dot text labels hover */}
                            <text 
                              x={x + 4} 
                              y={y + 1} 
                              className="fill-slate-300 font-bold text-[3px] select-none pointer-events-none drop-shadow"
                            >
                              {u.use_case_name.split(" ").slice(0, 2).join(" ")}
                            </text>
                            
                            {/* Hover tooltip structure */}
                            <title>{u.use_case_name} ({u.priority}) - Value: {u.value}, Complexity: {u.complexity}</title>
                          </g>
                        );
                      })}
                    </svg>

                    <div className="w-full flex items-center justify-between text-[8px] text-slate-500 uppercase tracking-widest font-bold mt-2">
                      <span>High Complexity</span>
                      <span>Low Complexity</span>
                    </div>
                  </div>
                </div>
              )}

              {/* E: AI Readiness Scores Breakdown (Radar & Bar charts) */}
              {insightsSubTab === "scoring" && (
                <div className="glass-panel p-6 rounded-2xl space-y-6">
                  <h3 className="text-base font-bold">7-Dimension Readiness Radar</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Radar Chart */}
                    <div className="h-[280px] flex items-center justify-center">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={getRadarData()}>
                          <PolarGrid stroke="#334155" />
                          <PolarAngleAxis dataKey="subject" tick={{ fill: "#64748b", fontSize: 9 }} />
                          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 8 }} />
                          <Radar name="Readiness Index" dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Bar Chart list */}
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={getBarData()} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis type="number" domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 8 }} />
                          <YAxis dataKey="subject" type="category" tick={{ fill: "#64748b", fontSize: 9 }} width={100} />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "8px", fontSize: 10 }}
                            content={({ active, payload, label }) => {
                              if (!active || !payload?.length) return null;
                              const point = payload[0]?.payload as { A?: number; justification?: string | null } | undefined;
                              return (
                                <div className="max-w-[240px] rounded-lg border border-slate-700 bg-slate-950 p-3 text-[10px] text-slate-200 shadow-xl">
                                  <p className="font-bold text-slate-100">{label}</p>
                                  <p className="mt-1 text-blue-300">Score: {int(point?.A ?? 0)}/100</p>
                                  {point?.justification && (
                                    <p className="mt-2 leading-relaxed text-slate-300">{point.justification}</p>
                                  )}
                                </div>
                              );
                            }}
                          />
                          <Bar dataKey="A" fill="#6366f1" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed pt-4 border-t border-slate-800">
                    <strong>Interpretation:</strong> {selectedAssessment.readiness_interpretation}
                  </p>
                  <p className="text-[10px] text-slate-500">
                    Scoring method: {selectedAssessment.scoring_method || "deterministic_rubric_v1"}
                    {selectedAssessment.scoring_rubric_version ? ` (${selectedAssessment.scoring_rubric_version})` : ""}.
                    {selectedAssessment.insufficient_evidence ? " Insufficient document evidence — scores are provisional." : " Dimension narrative uses evidence-derived justifications with explicit uncertainty."}
                    {selectedAssessment.automation_potential_basis ? ` Automation potential basis: ${selectedAssessment.automation_potential_basis}.` : ""}
                  </p>

                  {/* Detailed Dimension Explanations Stack */}
                  <div className="pt-6 border-t border-slate-800 space-y-4">
                    <h4 className="text-sm font-bold text-slate-200">Dimension Analysis & Action Plans</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[
                        { key: "data_readiness", subject: "Data Readiness", score: selectedAssessment.data_readiness },
                        { key: "process_readiness", subject: "Process Readiness", score: selectedAssessment.process_readiness },
                        { key: "integration_readiness", subject: "Integration Readiness", score: selectedAssessment.integration_readiness },
                        { key: "governance_readiness", subject: "Governance Readiness", score: selectedAssessment.governance_readiness },
                        { key: "security_readiness", subject: "Security Readiness", score: selectedAssessment.security_readiness },
                        { key: "team_readiness", subject: "Team Readiness", score: selectedAssessment.team_readiness },
                        { key: "business_alignment", subject: "Business Alignment", score: selectedAssessment.business_alignment }
                      ].map((dim) => {
                        const { explanation, recommendation, missing, uncertainty } = getReadinessDimensionExplanation(dim.subject, dim.score, dim.key);
                        const justification = getDimensionJustification(dim.key);
                        return (
                          <div key={dim.key} className="p-4 bg-slate-950/50 border border-slate-800 rounded-xl space-y-2">
                            <div className="flex items-center justify-between gap-3 flex-wrap">
                              <span className="text-xs font-bold text-slate-200">{dim.subject}</span>
                              {isReviewMode ? (
                                <div className="flex items-center gap-1.5">
                                  <input 
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={int(dim.score)}
                                    onChange={(e) => {
                                      const val = parseInt(e.target.value, 10);
                                      const updatedScore = isNaN(val) ? 0 : val;
                                      const newAssessment = { ...selectedAssessment, [dim.key]: updatedScore };
                                      // recalculate overall average score dynamically
                                      newAssessment.overall_score = recomputeWeightedOverall(newAssessment);
                                      setSelectedAssessment(newAssessment);
                                    }}
                                    className="w-16 md:w-24 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                                  />
                                  <input 
                                    type="number"
                                    min="0"
                                    max="100"
                                    value={int(dim.score)}
                                    onChange={(e) => {
                                      let val = parseInt(e.target.value, 10);
                                      if (isNaN(val)) val = 0;
                                      if (val > 100) val = 100;
                                      if (val < 0) val = 0;
                                      const newAssessment = { ...selectedAssessment, [dim.key]: val };
                                      newAssessment.overall_score = recomputeWeightedOverall(newAssessment);
                                      setSelectedAssessment(newAssessment);
                                    }}
                                    className="w-10 bg-slate-900 border border-slate-700 rounded text-center text-[10px] font-extrabold text-blue-400 focus:outline-none"
                                  />
                                </div>
                              ) : (
                                <span className={`text-xs font-extrabold ${dim.score >= 70 ? "text-emerald-400" : dim.score >= 50 ? "text-blue-400" : "text-amber-500"}`}>
                                  {int(dim.score)}/100
                                </span>
                              )}
                            </div>
                            {justification && (
                              <p className="text-[11px] text-slate-300 leading-relaxed">
                                <strong>Evidence:</strong> {justification}
                              </p>
                            )}
                            <p className="text-[11px] text-slate-400 leading-relaxed">
                              <strong>Status:</strong> {explanation}
                            </p>
                            <p className="text-[11px] text-amber-200/80 leading-relaxed">
                              <strong>Uncertainty:</strong> {uncertainty}
                            </p>
                            {missing.length > 0 && (
                              <p className="text-[11px] text-rose-300/80 leading-relaxed">
                                <strong>Missing evidence:</strong> {missing.join(" ")}
                              </p>
                            )}
                            <p className="text-[11px] text-blue-400 bg-blue-950/20 border border-blue-500/10 p-2 rounded leading-relaxed">
                              <strong>Recommendation:</strong> {recommendation}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* F: Risk & Governance Assessment */}
              {insightsSubTab === "risks" && (
                <div className="glass-panel p-6 rounded-2xl space-y-6">
                  <h3 className="text-base font-bold">Identified AI Risk Registry</h3>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 font-bold">
                          <th className="pb-3">Risk Name</th>
                          <th className="pb-3">Severity</th>
                          <th className="pb-3">Recommended Control</th>
                          <th className="pb-3 text-center">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {selectedAssessment.risks?.map((r, idx: number) => (
                          <tr key={idx} className="text-slate-300">
                            <td className="py-3 font-semibold">{r.risk_name}</td>
                            <td className="py-3 text-red-400 font-bold">{r.severity}</td>
                            <td className="py-3 text-slate-400">{r.recommendation}</td>
                            <td className="py-3 text-center">
                              {isReviewMode ? (
                                <input 
                                  type="checkbox"
                                  checked={r.is_control_met === 1}
                                  onChange={e => {
                                    const updatedRisks = [...selectedAssessment.risks];
                                    updatedRisks[idx].is_control_met = e.target.checked ? 1 : 0;
                                    setSelectedAssessment({...selectedAssessment, risks: updatedRisks});
                                  }}
                                  className="w-3.5 h-3.5 accent-emerald-500 cursor-pointer"
                                />
                              ) : (
                                <span className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase ${r.is_control_met === 1 ? "bg-emerald-950 text-emerald-400 border border-emerald-500/20" : "bg-red-950 text-red-400 border border-red-500/20"}`}>
                                  {r.is_control_met === 1 ? "Audit Met" : "Gaps Open"}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl">
                    <h4 className="text-xs font-bold text-slate-300 mb-2">Required Compliance Control Checklist</h4>
                    <div className="space-y-2 text-xs text-slate-400">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
                        <span>PII Masking and Sanitization gates compiled</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
                        <span>GDPR suppression audit trails active</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-slate-700 shrink-0" />
                        <span>Human-in-the-loop scoring validation threshold active</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* G: Recommended First Pilot */}
              {insightsSubTab === "pilot" && (
                <div className="p-6 bg-gradient-to-r from-blue-950/40 to-indigo-950/40 border border-blue-500/30 rounded-2xl relative overflow-hidden">
                  <div className="absolute -top-12 -right-12 w-48 h-48 bg-blue-500/10 rounded-full blur-2xl animate-pulse-glow" />
                  
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-6 h-6 text-blue-400 glow-subtle animate-bounce" />
                    <span className="text-xs uppercase font-extrabold tracking-wider text-blue-400">Recommended First Pilot Proposal</span>
                  </div>

                  {isReviewMode ? (
                    <div className="space-y-3 mb-4">
                      <div>
                        <label className="block text-[10px] text-slate-400 font-bold uppercase mb-0.5">Pilot Proposal Title</label>
                        <input 
                          type="text"
                          value={selectedAssessment.recommended_first_pilot || ""}
                          onChange={e => setSelectedAssessment({ ...selectedAssessment, recommended_first_pilot: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none"
                        />
                      </div>
                    </div>
                  ) : (
                    <h3 className="text-lg font-bold text-white mb-2">{selectedAssessment.recommended_first_pilot}</h3>
                  )}
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <div className="p-4 bg-slate-950/50 rounded-xl border border-slate-800">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Strategic Justification (Why this pilot)</span>
                      {isReviewMode ? (
                        <textarea 
                          value={selectedAssessment.why_recommended_pilot || ""}
                          onChange={e => setSelectedAssessment({ ...selectedAssessment, why_recommended_pilot: e.target.value })}
                          className="w-full h-24 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none"
                        />
                      ) : (
                        <p className="text-xs text-slate-300 leading-relaxed">{selectedAssessment.why_recommended_pilot}</p>
                      )}
                    </div>
                    <div className="p-4 bg-slate-950/50 rounded-xl border border-slate-800 flex flex-col justify-between">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Estimated Impact</span>
                        {isReviewMode ? (
                          <textarea 
                            value={selectedAssessment.expected_pilot_impact || ""}
                            onChange={e => setSelectedAssessment({ ...selectedAssessment, expected_pilot_impact: e.target.value })}
                            className="w-full h-24 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none"
                          />
                        ) : (
                          <p className="text-xs text-slate-300 leading-relaxed">{selectedAssessment.expected_pilot_impact}</p>
                        )}
                      </div>
                      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-[10px]">
                        <span className="text-slate-400">Score confidence:</span>
                        <span className="text-emerald-400 font-extrabold text-sm">{selectedAssessment.confidence_score}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* H: Roadmap Timeline Generator */}
              {insightsSubTab === "roadmap" && (
                <div className="glass-panel p-6 rounded-2xl">
                  <h3 className="text-base font-bold mb-6">90-Day Implementation Roadmap</h3>
                  
                  <div className="space-y-6 pl-6 border-l-2 border-dashed border-blue-500/30 relative">
                    {selectedAssessment.roadmap_items?.map((item, idx: number) => (
                      <div key={idx} className="relative">
                        {/* Bullet circle */}
                        <div className="absolute -left-[35px] top-0 w-6 h-6 rounded-full bg-blue-600 border-4 border-slate-950 flex items-center justify-center text-[9px] font-bold text-white">
                          {idx + 1}
                        </div>

                        <div className="p-4 bg-slate-900/30 border border-slate-800 hover:border-slate-700 transition-all rounded-xl space-y-2">
                          <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest">{item.phase}</span>
                          {isReviewMode ? (
                            <div className="space-y-2 pt-1">
                              <input 
                                type="text"
                                value={item.action_item || ""}
                                onChange={e => {
                                  const updated = [...selectedAssessment.roadmap_items];
                                  updated[idx].action_item = e.target.value;
                                  setSelectedAssessment({ ...selectedAssessment, roadmap_items: updated });
                                }}
                                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none"
                                placeholder="Action Item"
                              />
                              <input 
                                type="text"
                                value={item.expected_impact || ""}
                                onChange={e => {
                                  const updated = [...selectedAssessment.roadmap_items];
                                  updated[idx].expected_impact = e.target.value;
                                  setSelectedAssessment({ ...selectedAssessment, roadmap_items: updated });
                                }}
                                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none"
                                placeholder="Expected Impact"
                              />
                            </div>
                          ) : (
                            <>
                              <h4 className="text-sm font-bold text-slate-200 mt-1">{item.action_item}</h4>
                              <p className="text-xs text-slate-400 mt-2"><strong>Impact:</strong> {item.expected_impact}</p>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Commercial Strategy Sub-Tab */}
              {insightsSubTab === "commercial" && (() => {
                const rec = getEngagementRecommendation();
                const pricing = getCalibratedPricing(rec);
                const justifications = getPricingJustifications();
                const team = getDeliveryTeam(rec.model);

                const architectureLayers = [
                  {
                    id: "systems",
                    label: "Client Documents & Systems",
                    purpose: "Establish data access over existing corporate files and business databases.",
                    components: "Proprietary playbook PDFs, Word templates, incident ticket histories, Salesforce pipeline objects.",
                    controls: "Restricted read-only database connections, local staging storage, tenant separation."
                  },
                  {
                    id: "ingestion",
                    label: "Ingestion & Parsing Layer",
                    purpose: "Clean, chunk, and extract structural metadata from unstructured files.",
                    components: "OCR document parsers, layout-aware markdown splitters, semantic chunking pipelines.",
                    controls: "File size validation limits, automated PII scrubbing (regex filters), source file hash tracking."
                  },
                  {
                    id: "knowledge",
                    label: "Knowledge Base / Vector Store",
                    purpose: "Index documents to support low-latency semantic keyword and context retrieval.",
                    components: "ChromaDB, Pinecone, or PostgreSQL pgvector store; OpenAI text-embedding-3-small embeddings.",
                    controls: "Strict partition checks on tenant_id, data encryption-at-rest, automatic vector pruning."
                  },
                  {
                    id: "orchestration",
                    label: "LLM Orchestration Layer",
                    purpose: "Run stateful multi-agent pipelines to generate grounded solution plans and opportunity maps.",
                    components: "LangGraph workflows, state managers, system prompt routers, context-window managers.",
                    controls: "Input rate limits, fallbacks to local fallback agents during API timeouts, context window size audits."
                  },
                  {
                    id: "guardrails",
                    label: "Guardrails & Human Review",
                    purpose: "Protect organizational credibility by filtering hallucinations and enabling consultant audit overrides.",
                    components: "Regex sanitizers, custom toxic classifications, in-console consultant approval screens.",
                    controls: "Block models from saving directly to final exports, require 'approved' tag toggle in Human Review Mode."
                  },
                  {
                    id: "copilot",
                    label: "Business Copilot Interface",
                    purpose: "Expose secure advisory dashboards, opportunity maps, and roadmap timeline controls to consultants.",
                    components: "Next.js 15 Tailwind/CSS UI, React charts (radar, bar), strategy asset generator download modules.",
                    controls: "OAuth2 authentication with JWT tokens, session lifecycle timeout, complete action audit logging."
                  },
                  {
                    id: "monitoring",
                    label: "Monitoring & Governance",
                    purpose: "Track model accuracy, performance delays, token expenditures, and user feedback.",
                    components: "Arize Phoenix, LangSmith dashboard integrations, custom user correction logs.",
                    controls: "Automatic threshold alarms for latency > 5s, token burn rate caps, periodic drift eval audits."
                  }
                ];

                return (
                  <div className="space-y-6 animate-fade-in">
                    <div>
                      <h3 className="text-base font-bold flex items-center gap-2">
                        <Coins className="w-5 h-5 text-blue-500 glow-subtle" />
                        <span>Commercial Strategy &amp; Implementation Architecture</span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Dynamic commercial scoping and target blueprints translating readiness indexes into strategic engagement plans.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      
                      {/* Left Side: Scoping & Investment */}
                      <div className="lg:col-span-2 space-y-6">
                        
                        {/* Engagement Model & Pricing Card */}
                        <div className="glass-panel p-6 rounded-2xl bg-gradient-to-r from-blue-950/20 to-indigo-950/20 border-blue-500/20 relative overflow-hidden">
                          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-2xl rounded-full" />
                          
                          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4 mb-4">
                            <div>
                              <span className="text-[10px] uppercase font-extrabold text-blue-400 tracking-wider">Recommended Engagement Model</span>
                              <h4 className="text-lg font-bold text-slate-100 mt-1">{rec.model}</h4>
                            </div>
                            <div className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-2 text-right">
                              <span className="text-[10px] uppercase font-bold text-slate-500 block">Indicative Investment</span>
                              <span className="text-xl font-extrabold text-gradient">{pricing}</span>
                            </div>
                          </div>

                          <div className="space-y-3">
                            <div>
                              <span className="text-[10px] text-slate-400 font-bold uppercase">Strategic Focus:</span>
                              <p className="text-xs text-slate-200 font-semibold mt-0.5">{rec.pilotName}</p>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-400 font-bold uppercase">Model Rationale:</span>
                              <p className="text-xs text-slate-300 leading-relaxed mt-0.5">{rec.rationale}</p>
                            </div>
                            <div className="mt-4 pt-3 border-t border-slate-800 flex items-center gap-2 text-[10px] text-slate-400">
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                              <span>
                                <strong>Scoping Disclaimer:</strong> Range is indicative, assumption-based, and subject to discovery validation.
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Pricing Justification Panel */}
                        <div className="glass-panel p-5 rounded-2xl space-y-4">
                          <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Scoping &amp; Pricing Justification</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {justifications.map((item, idx) => (
                              <div key={idx} className="p-3 bg-slate-950/50 border border-slate-800 rounded-xl space-y-1">
                                <span className="text-xs font-bold text-slate-200 block">{item.title}</span>
                                <p className="text-[10px] text-slate-400 leading-relaxed">{item.desc}</p>
                              </div>
                            ))}
                          </div>
                        </div>

                      </div>

                      {/* Right Side: Suggested Team Structure */}
                      <div className="glass-panel p-5 rounded-2xl space-y-4">
                        <div>
                          <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Recommended Delivery Team</h4>
                          <p className="text-[10px] text-slate-400 mt-1">Strategic resource structuring calibrated for engagement execution.</p>
                        </div>

                        <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
                          {team.map((res, idx) => (
                            <div key={idx} className="p-3 bg-slate-900/40 border border-slate-800 rounded-xl space-y-1.5 hover:border-slate-700 transition-all">
                              <div className="flex justify-between items-center gap-2">
                                <span className="text-xs font-bold text-slate-200">{res.role}</span>
                                <span className="text-[9px] bg-blue-950/50 border border-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded font-extrabold">{res.load} Allocation</span>
                              </div>
                              <p className="text-[10px] text-slate-400 leading-relaxed">{res.task}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                    </div>

                    {/* Implementation Architecture Chevron Section */}
                    <div className="glass-panel p-6 rounded-2xl space-y-6">
                      <div>
                        <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Target Implementation Architecture</h4>
                        <p className="text-[10px] text-slate-400 mt-1">Recommended end-to-end data pipelines, orchestration layers, and human gates.</p>
                      </div>

                      {/* Chevrons Flow */}
                      <div className="flex flex-wrap lg:flex-nowrap gap-2 items-center justify-between">
                        {architectureLayers.map((layer, idx) => {
                          const active = activeArchLayer === layer.id;
                          return (
                            <React.Fragment key={layer.id}>
                              <button
                                onClick={() => setActiveArchLayer(layer.id)}
                                className={`flex-1 min-w-[120px] text-left p-3 rounded-xl border transition-all relative ${active ? "bg-blue-950/20 border-blue-500 text-white glow-subtle" : "bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700"}`}
                              >
                                <span className="text-[9px] text-slate-500 font-extrabold block uppercase mb-1">Layer {idx + 1}</span>
                                <span className="text-[10px] font-bold block leading-tight">{layer.label}</span>
                                {active && (
                                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-blue-500 rotate-45" />
                                )}
                              </button>
                              {idx < architectureLayers.length - 1 && (
                                <ArrowRight className="w-4 h-4 text-slate-700 shrink-0 hidden lg:block" />
                              )}
                            </React.Fragment>
                          );
                        })}
                      </div>

                      {/* Selected Layer Details Panel */}
                      {(() => {
                        const currentLayer = architectureLayers.find(l => l.id === activeArchLayer) ?? architectureLayers[0];
                        return (
                          <div className="p-5 bg-slate-950 border border-slate-800 rounded-xl grid grid-cols-1 md:grid-cols-3 gap-6 animate-fade-in">
                            <div className="space-y-1">
                              <span className="text-[9px] uppercase font-bold text-blue-400 block tracking-wider">Operational Purpose</span>
                              <h5 className="text-sm font-bold text-slate-200">{currentLayer.label}</h5>
                              <p className="text-xs text-slate-400 mt-2 leading-relaxed">{currentLayer.purpose}</p>
                            </div>
                            <div className="space-y-1 border-t md:border-t-0 md:border-l border-slate-800 pt-4 md:pt-0 md:pl-6">
                              <span className="text-[9px] uppercase font-bold text-emerald-400 block tracking-wider">Recommended Components</span>
                              <p className="text-xs text-slate-300 mt-2 leading-relaxed">{currentLayer.components}</p>
                            </div>
                            <div className="space-y-1 border-t md:border-t-0 md:border-l border-slate-800 pt-4 md:pt-0 md:pl-6">
                              <span className="text-[9px] uppercase font-bold text-amber-500 block tracking-wider">Risk &amp; Control Considerations</span>
                              <p className="text-xs text-slate-300 mt-2 leading-relaxed">{currentLayer.controls}</p>
                            </div>
                          </div>
                        );
                      })()}
                    </div>

                    {/* Phased Plan & Expansion Path */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      
                      {/* Phased Plan */}
                      <div className="glass-panel p-5 rounded-2xl space-y-4">
                        <div>
                          <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Phase-Wise Delivery Plan</h4>
                          <p className="text-[10px] text-slate-400 mt-1">Standardized implementation sequence from initial discovery through scaling.</p>
                        </div>

                        <div className="space-y-4 relative pl-4 border-l border-slate-800 mt-2">
                          {[
                            { phase: "Phase 1: Discovery & Design", dur: "1–2 weeks", desc: "Confirm pilot boundaries, map data directories, establish compliance baselines, and design prompt architectures." },
                            { phase: "Phase 2: MVP Build", dur: "3–6 weeks", desc: "Construct operational ingestion workflows, mount primary prompt graphs, and integrate human override controls." },
                            { phase: "Phase 3: Validation & Eval", dur: "2–4 weeks", desc: "Audit model drift metrics, execute internal red-teaming, run user tests, and confirm data security." },
                            { phase: "Phase 4: Scaling & Rollout", dur: "4–8 weeks", desc: "Secure multi-tenant deploy, launch enterprise training clinics, enforce token spend limit triggers, and establish helpdesks." }
                          ].map((ph, idx) => (
                            <div key={idx} className="relative space-y-1">
                              <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-blue-600 border-2 border-slate-950" />
                              <div className="flex justify-between items-center gap-2">
                                <span className="text-xs font-bold text-slate-200">{ph.phase}</span>
                                <span className="text-[9px] font-bold text-blue-400 bg-blue-950/20 px-1.5 py-0.5 rounded border border-blue-500/10">{ph.dur}</span>
                              </div>
                              <p className="text-[10px] text-slate-400 leading-relaxed">{ph.desc}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Expansion Path */}
                      <div className="glass-panel p-5 rounded-2xl space-y-4">
                        <div>
                          <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Enterprise Scaling &amp; Expansion Path</h4>
                          <p className="text-[10px] text-slate-400 mt-1">Multi-stage expansion roadmaps turning initial pilots into full AI operating ecosystems.</p>
                        </div>

                        {/* Progression Stepper */}
                        <div className="grid grid-cols-1 gap-3 mt-2">
                          {[
                            { step: "Step 1: Immediate Pilot Focus", label: rec.pilotName, desc: "Solve near-term friction and build baseline trust." },
                            { step: "Step 2: Near-Term Scaling", label: "Internal Advisory Knowledge Assistant", desc: "Scale semantic document grounding across multi-department files." },
                            { step: "Step 3: Process Optimization", label: "Autonomous Support Triage Router", desc: "Automate incident logs routing and ticket classification pipeline." },
                            { step: "Step 4: Continuous Audits", label: "Contract Policy Audit Assistant", desc: " GDPR-compliant contract policy scanning on supplier files." },
                            { step: "Step 5: Full Maturity Model", label: "AI Governance & Token Dashboard", desc: "Centrally track LLM spends, accuracy metrics, and security logs." }
                          ].map((prog, idx) => (
                            <div key={idx} className="flex gap-3 items-start p-2.5 bg-slate-900/40 border border-slate-800 rounded-xl hover:border-slate-700 transition-all">
                              <div className="w-5 h-5 rounded bg-blue-950/50 border border-blue-500/20 flex items-center justify-center text-[10px] font-extrabold text-blue-400 shrink-0">
                                {idx + 1}
                              </div>
                              <div className="space-y-0.5">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="text-[9px] uppercase font-bold text-slate-500">{prog.step}</span>
                                  <span className="text-slate-700 text-xs">•</span>
                                  <span className="text-[10px] text-blue-400 font-bold">{prog.label}</span>
                                </div>
                                <p className="text-[10px] text-slate-400 leading-relaxed">{prog.desc}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                    </div>
                  </div>
                );
              })()}

              {insightsSubTab === "investment" && (() => {
                const opps = investmentPackage?.opportunities || [];
                const selected =
                  opps.find((o) => o.id === selectedOpportunityId) || opps[0] || null;
                const finance = selected?.financial_evaluation;
                const base = finance?.scenarios?.base;
                const pilot = investmentPackage?.pilot_recommendation;
                const decision = investmentPackage?.decision_summary;
                return (
                  <div className="space-y-6 animate-fade-in">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-base font-bold flex items-center gap-2">
                          <TrendingUp className="w-5 h-5 text-blue-500" />
                          <span>Investment Intelligence</span>
                        </h3>
                        <p className="text-xs text-slate-400 mt-1">
                          Deterministic opportunity ranking, financial feasibility, pilot recommendation, and investment decision.
                        </p>
                      </div>
                      <button
                        onClick={() => selectedAssessment && loadInvestmentIntelligence(selectedAssessment.id)}
                        className="text-[10px] px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-900"
                        disabled={investmentBusy}
                      >
                        {investmentBusy ? "Loading…" : "Refresh"}
                      </button>
                    </div>

                    {investmentMessage && (
                      <div className="text-xs text-amber-300 bg-amber-950/30 border border-amber-500/20 rounded-lg px-3 py-2">
                        {investmentMessage}
                      </div>
                    )}

                    <div className="glass-panel p-4 rounded-2xl grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div>
                        <div className="text-[10px] uppercase text-slate-500 font-bold">Decision</div>
                        <div className="text-sm font-bold text-slate-100 mt-1">{decision?.status || "pending"}</div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase text-slate-500 font-bold">Prioritization rubric</div>
                        <div className="text-sm font-bold text-slate-100 mt-1">{investmentPackage?.prioritization_rubric_version || "—"}</div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase text-slate-500 font-bold">Financial model</div>
                        <div className="text-sm font-bold text-slate-100 mt-1">{investmentPackage?.financial_model_version || "—"}</div>
                      </div>
                      <p className="md:col-span-3 text-xs text-slate-400">{decision?.explanation || "No decision explanation yet."}</p>
                    </div>

                    <div className="glass-panel p-4 rounded-2xl overflow-x-auto">
                      <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest mb-3">Opportunity Portfolio</h4>
                      <table className="w-full text-left text-xs">
                        <thead className="text-slate-500">
                          <tr>
                            <th className="py-2 pr-2">Rank</th>
                            <th className="py-2 pr-2">Opportunity</th>
                            <th className="py-2 pr-2">Priority</th>
                            <th className="py-2 pr-2">Feasibility</th>
                            <th className="py-2 pr-2">Investment</th>
                            <th className="py-2 pr-2">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {opps.map((opp) => {
                            const inv = opp.financial_evaluation?.scenarios?.base?.implementation_investment;
                            const complete = opp.financial_evaluation?.evaluation_complete;
                            return (
                              <tr
                                key={opp.id || opp.use_case_name}
                                className={`border-t border-slate-800 cursor-pointer hover:bg-slate-900/50 ${selectedOpportunityId === opp.id ? "bg-blue-950/20" : ""}`}
                                onClick={() => {
                                  setSelectedOpportunityId(opp.id ?? null);
                                  const inputs = (opp.financial_inputs || {}) as Record<string, unknown>;
                                  setFinanceDraft({
                                    monthly_volume: inputs.monthly_volume != null ? String(inputs.monthly_volume) : "",
                                    effort_minutes_per_transaction: inputs.effort_minutes_per_transaction != null ? String(inputs.effort_minutes_per_transaction) : "",
                                    loaded_hourly_cost: inputs.loaded_hourly_cost != null ? String(inputs.loaded_hourly_cost) : "",
                                    automation_rate: inputs.automation_rate != null ? String(inputs.automation_rate) : "",
                                    adoption_rate: inputs.adoption_rate != null ? String(inputs.adoption_rate) : "",
                                    implementation_cost: inputs.implementation_cost != null ? String(inputs.implementation_cost) : "",
                                    integration_cost: inputs.integration_cost != null ? String(inputs.integration_cost) : "",
                                    cloud_llm_monthly_cost: inputs.cloud_llm_monthly_cost != null ? String(inputs.cloud_llm_monthly_cost) : "",
                                    currency: String(inputs.currency || "USD"),
                                  });
                                }}
                              >
                                <td className="py-2 pr-2">{opp.ranking ?? "—"}</td>
                                <td className="py-2 pr-2 font-semibold text-slate-200">{opp.use_case_name || opp.name}</td>
                                <td className="py-2 pr-2">{opp.weighted_priority_score ?? "—"}</td>
                                <td className="py-2 pr-2">{opp.feasibility?.proposed_approach || "—"}</td>
                                <td className="py-2 pr-2">{complete ? `${opp.financial_evaluation?.currency || ""} ${inv?.toLocaleString() ?? "n/a"}` : "Incomplete"}</td>
                                <td className="py-2 pr-2">{opp.is_blocked ? "blocked" : opp.recommendation_status}</td>
                              </tr>
                            );
                          })}
                          {!opps.length && (
                            <tr>
                              <td colSpan={6} className="py-4 text-slate-500 text-center">
                                No evaluated opportunities yet. Run document analysis first.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>

                    {selected && (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="glass-panel p-4 rounded-2xl space-y-3">
                          <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Opportunity Detail</h4>
                          <p className="text-sm font-bold text-slate-100">{selected.use_case_name || selected.name}</p>
                          <p className="text-xs text-slate-400">{selected.ranking_explanation}</p>
                          <p className="text-xs text-slate-300">{selected.feasibility?.approach_rationale}</p>
                          {(selected.hard_blockers || []).length > 0 && (
                            <div className="text-xs text-red-300 bg-red-950/20 border border-red-500/20 rounded-lg p-2">
                              Blockers: {(selected.hard_blockers || []).map((b) => b.description || b.code).join("; ")}
                            </div>
                          )}
                          {(selected.missing_information || []).length > 0 && (
                            <div className="text-[10px] text-amber-200">
                              Missing: {(selected.missing_information || []).slice(0, 6).join(" · ")}
                            </div>
                          )}
                          <div className="grid grid-cols-2 gap-2">
                            {Object.entries(selected.criterion_scores || {}).map(([key, meta]) => (
                              <div key={key} className="bg-slate-950/50 border border-slate-800 rounded-lg p-2">
                                <div className="text-[9px] uppercase text-slate-500">{key.split("_").join(" ")}</div>
                                <div className="text-xs font-bold text-slate-200">{meta.score ?? "—"}</div>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="glass-panel p-4 rounded-2xl space-y-3">
                          <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Financial Model</h4>
                          {!finance?.evaluation_complete && (
                            <p className="text-xs text-amber-300">
                              {finance?.incomplete_message || "Financial evaluation incomplete — additional baseline information required."}
                            </p>
                          )}
                          <div className="grid grid-cols-2 gap-2">
                            {Object.entries(financeDraft).map(([key, value]) => (
                              <label key={key} className="text-[10px] text-slate-400 space-y-1">
                                <span className="block uppercase tracking-wide">{key.split("_").join(" ")}</span>
                                <input
                                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-200"
                                  value={value}
                                  onChange={(e) => setFinanceDraft((prev) => ({ ...prev, [key]: e.target.value }))}
                                />
                              </label>
                            ))}
                          </div>
                          <button
                            onClick={saveOpportunityFinancials}
                            disabled={investmentBusy || !isReviewMode}
                            className="text-xs px-3 py-2 rounded-lg bg-blue-600 text-white font-bold disabled:opacity-40"
                          >
                            Recalculate ROI
                          </button>
                          {!isReviewMode && (
                            <p className="text-[10px] text-slate-500">Enable Human Review Mode to edit assumptions.</p>
                          )}
                          {finance?.evaluation_complete && base && (
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div className="bg-slate-950/60 rounded-lg p-2">ROI (base): <strong>{base.roi_percentage ?? "n/a"}%</strong></div>
                              <div className="bg-slate-950/60 rounded-lg p-2">Payback: <strong>{base.payback_months ?? "n/a"} mo</strong></div>
                              <div className="bg-slate-950/60 rounded-lg p-2">Net annual: <strong>{base.net_annual_savings?.toLocaleString() ?? "n/a"}</strong></div>
                              <div className="bg-slate-950/60 rounded-lg p-2">Investment: <strong>{base.implementation_investment?.toLocaleString() ?? "n/a"}</strong></div>
                            </div>
                          )}
                          {(finance?.sensitivity || []).length > 0 && (
                            <div className="text-[10px] text-slate-400 max-h-28 overflow-y-auto">
                              Sensitivity: {(finance?.sensitivity || []).slice(0, 8).map((s, idx) => (
                                <div key={idx}>{s.parameter} {s.delta_pct}% → ROI {s.resulting_roi_pct ?? "n/a"}%</div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      <div className="glass-panel p-4 rounded-2xl space-y-2">
                        <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Pilot Recommendation</h4>
                        <p className="text-sm font-bold text-slate-100">{pilot?.opportunity_name || "Not selected"}</p>
                        <p className="text-xs text-slate-400">{pilot?.selection_rationale}</p>
                        <p className="text-xs text-slate-300">{pilot?.estimated_investment_label}</p>
                        <p className="text-xs text-slate-300">{pilot?.time_to_value_label}</p>
                        <div className="space-y-1">
                          {(pilot?.success_metrics || []).map((m, idx) => (
                            <div key={idx} className="text-[10px] text-slate-400 border border-slate-800 rounded-lg p-2">
                              <strong className="text-slate-200">{m.name}</strong>: {m.baseline} → {m.target}
                            </div>
                          ))}
                        </div>
                        <div className="space-y-1 max-h-40 overflow-y-auto">
                          {(pilot?.stages || []).map((s, idx) => (
                            <div key={idx} className="text-[10px] text-slate-400">
                              <strong className="text-slate-300">{String(s.name)}</strong> — {String(s.objective || "")}
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="glass-panel p-4 rounded-2xl space-y-3">
                        <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest">Decision Summary</h4>
                        <select
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-2 text-xs text-slate-200"
                          value={decisionDraft.status}
                          disabled={!isReviewMode}
                          onChange={(e) => setDecisionDraft((prev) => ({ ...prev, status: e.target.value }))}
                        >
                          <option value="invest">Invest</option>
                          <option value="validate_first">Validate First</option>
                          <option value="defer">Defer</option>
                          <option value="not_recommended">Not Recommended</option>
                          <option value="pending_review">Pending Review</option>
                        </select>
                        <textarea
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-2 text-xs text-slate-200 min-h-24"
                          disabled={!isReviewMode}
                          value={decisionDraft.explanation}
                          onChange={(e) => setDecisionDraft((prev) => ({ ...prev, explanation: e.target.value }))}
                          placeholder="Explain the investment decision and any missing evidence"
                        />
                        <button
                          onClick={saveInvestmentDecision}
                          disabled={investmentBusy || !isReviewMode || decisionDraft.explanation.trim().length < 3}
                          className="text-xs px-3 py-2 rounded-lg bg-emerald-600 text-white font-bold disabled:opacity-40"
                        >
                          Record Decision
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* I: Strategy Asset Generator export downloads panel */}
              {insightsSubTab === "export" && (
                <div className="glass-panel p-6 rounded-2xl space-y-6">
                  <h3 className="text-base font-bold">Strategy Asset Generator</h3>
                  <p className="text-xs text-slate-400">One-click compile triggers producing production-ready deliverables.</p>

                  {!canExport && (
                    <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4 text-xs text-amber-200">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                        <div>
                          <p className="font-semibold">Please approve this assessment in Human Review Mode before generating client-ready assets.</p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setIsReviewMode(true);
                                setInsightsSubTab("summary");
                              }}
                              className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[11px] font-bold text-amber-100 transition-colors hover:bg-amber-500/20"
                            >
                              Open Review Controls
                            </button>
                            <span className="self-center text-[11px] text-amber-300/80">
                              Set status to <strong>Approved</strong> and click <strong>Save Manual Edits</strong>.
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    
                    <div className="p-4 bg-slate-900/30 border border-slate-800 rounded-xl flex flex-col justify-between h-44">
                      <div>
                        <div className="p-1.5 bg-red-950/40 border border-red-500/20 text-red-400 w-fit rounded-lg mb-2">
                          <FileText className="w-5 h-5" />
                        </div>
                        <h4 className="text-xs font-bold text-slate-200">AI Readiness Report</h4>
                        <p className="text-[10px] text-slate-400 mt-1">CSS-rich diagnostic scorecard PDF summarizing assessments.</p>
                      </div>
                      <button 
                        onClick={() => handleDownload("pdf")}
                        disabled={!canExport}
                        className={`w-full rounded-lg py-2 text-xs font-bold transition-colors flex items-center justify-center gap-1 ${canExport ? "bg-red-600 hover:bg-red-700 text-white" : "cursor-not-allowed bg-slate-800 text-slate-500"}`}
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Generate PDF Report</span>
                      </button>
                    </div>

                    <div className="p-4 bg-slate-900/30 border border-slate-800 rounded-xl flex flex-col justify-between h-44">
                      <div>
                        <div className="p-1.5 bg-blue-950/40 border border-blue-500/20 text-blue-400 w-fit rounded-lg mb-2">
                          <FileText className="w-5 h-5" />
                        </div>
                        <h4 className="text-xs font-bold text-slate-200">Pilot Proposal</h4>
                        <p className="text-[10px] text-slate-400 mt-1">MS Word document (DOCX) featuring solution structures.</p>
                      </div>
                      <button 
                        onClick={() => handleDownload("docx")}
                        disabled={!canExport}
                        className={`w-full rounded-lg py-2 text-xs font-bold transition-colors flex items-center justify-center gap-1 ${canExport ? "bg-blue-600 hover:bg-blue-700 text-white" : "cursor-not-allowed bg-slate-800 text-slate-500"}`}
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Generate DOCX Proposal</span>
                      </button>
                    </div>

                    <div className="p-4 bg-slate-900/30 border border-slate-800 rounded-xl flex flex-col justify-between h-44">
                      <div>
                        <div className="p-1.5 bg-amber-950/40 border border-amber-500/20 text-amber-400 w-fit rounded-lg mb-2">
                          <FileText className="w-5 h-5" />
                        </div>
                        <h4 className="text-xs font-bold text-slate-200">Executive Board Deck</h4>
                        <p className="text-[10px] text-slate-400 mt-1">PowerPoint deck (PPTX) with custom gradient covers.</p>
                      </div>
                      <button 
                        onClick={() => handleDownload("pptx")}
                        disabled={!canExport}
                        className={`w-full rounded-lg py-2 text-xs font-bold transition-colors flex items-center justify-center gap-1 ${canExport ? "bg-amber-600 hover:bg-amber-700 text-white" : "cursor-not-allowed bg-slate-800 text-slate-500"}`}
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Generate PPTX Board Deck</span>
                      </button>
                    </div>

                  </div>
                </div>
              )}

              {insightsSubTab === "proposal" && (
                <ProposalSowEditor
                  payload={proposalSow}
                  busy={workspaceBusy}
                  message={workspaceMessage}
                  onGenerate={handleGenerateProposalSow}
                  onExport={handleExportProposalSow}
                />
              )}

              {insightsSubTab === "workflow" && (
                <ReviewApprovalPanel
                  workflowStatus={selectedAssessment?.workflow_status}
                  approvalStatus={selectedAssessment?.approval_status}
                  investmentStatus={selectedAssessment?.investment_decision_status}
                  locked={Boolean(selectedAssessment?.locked_for_delivery)}
                  busy={workspaceBusy}
                  onWorkflowChange={handleWorkflowUpdate}
                />
              )}

            </div>
          </div>
        )}

      </div>

      {/* FOOTER */}
      <footer className="w-full border-t border-white/5 py-4 px-6 text-center text-[10px] text-slate-500">
        <span>© 2026 AI Readiness Intelligence Studio &nbsp;|&nbsp; Tagline: &quot;From business documents to AI opportunity roadmap in minutes.&quot;</span>
      </footer>
    </div>
  );
}

// Utility to convert floats/strings to simple integers
function int(val: string | number | null | undefined) {
  const parsed = parseInt(String(val ?? 0), 10);
  return isNaN(parsed) ? 0 : parsed;
}
