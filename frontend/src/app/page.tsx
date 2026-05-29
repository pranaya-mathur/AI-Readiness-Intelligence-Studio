"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  ArrowRight, Plus, FileText, CheckCircle, TrendingUp, 
  BarChart3, Brain, Shield, Calendar, Download, Edit3, Save, 
  UploadCloud, Sparkles, RefreshCw, Trash2, AlertTriangle, LogOut
} from "lucide-react";
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
  process_readiness: number;
  integration_readiness: number;
  governance_readiness: number;
  security_readiness: number;
  team_readiness: number;
  business_alignment: number;
  business_summary: string | null;
  client_summary: string | null;
  reviewer_notes: string | null;
  approval_status: string | null;
  readiness_interpretation: string | null;
  created_at: string;
  updated_at: string;
  bottlenecks: Bottleneck[];
  use_cases: UseCase[];
  risks: Risk[];
  roadmap_items: RoadmapItem[];
  extracted_signals: ExtractedSignal[];
  client: ClientWorkspace | null;
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

  const [activeTab, setActiveTab] = useState("dashboard"); // dashboard, intake, upload, insights
  const [insightsSubTab, setInsightsSubTab] = useState("summary"); // summary, bottlenecks, opportunity, matrix, scoring, risks, pilot, roadmap, export
  
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

  const getReadinessDimensionExplanation = (subject: string, score: number) => {
    const currentTools = selectedAssessment?.current_tools || [];
    const painPoints = selectedAssessment?.pain_points || [];
    const compliance = selectedAssessment?.compliance_requirements || [];
    
    const toolsStr = currentTools.length > 0 ? currentTools.join(", ") : "internal legacy tools";
    const painStr = painPoints.length > 0 ? painPoints.slice(0, 2).join(" and ").toLowerCase() : "manual coordination friction";
    const compStr = compliance.length > 0 ? compliance.join(", ") : "general industry baselines";

    switch(subject) {
      case "Data Readiness":
        if (score >= 70) {
          return {
            explanation: `Structured data sources are reasonably well-defined in existing tools like ${toolsStr}, creating a viable foundation for ingestion.`,
            recommendation: "Establish automated data pipelines and data ingestion scrubbers to maintain high-quality vectors for LLM context windows."
          };
        } else {
          return {
            explanation: `Data exists across business systems, but fragmentation across ${toolsStr} limits immediate AI scaling due to manual silos and inconsistent formatting.`,
            recommendation: "Centralize corporate knowledge databases into structured cloud directories and consolidate scattered team spreadsheets."
          };
        }
      case "Process Readiness":
        if (score >= 70) {
          return {
            explanation: "Core business workflows are structured, with clean handoff points and standardized steps suitable for immediate agent routing.",
            recommendation: "Deploy shadow AI models to test auto-classification in live operations before replacing manual routing entirely."
          };
        } else {
          return {
            explanation: `Several workflows in scoping scope are highly repetitive and prone to ${painStr}, but lack formal process standardization before scaling.`,
            recommendation: "Document step-by-step operating guidelines for proposal drafting and ticket routing to prepare structured templates for AI mapping."
          };
        }
      case "Integration Readiness":
        if (score >= 70) {
          return {
            explanation: `Existing stack (${toolsStr}) supports standard REST/GraphQL APIs, allowing AI agents to query and write data seamlessly.`,
            recommendation: "Register customized webhook triggers and develop lightweight middleware integrations to track automated actions."
          };
        } else {
          return {
            explanation: `Existing tools provide base integration potential, but lack cohesive middleware pipelines, resulting in manual copy-paste routines.`,
            recommendation: "Build dedicated middleware endpoints or leverage unified connector APIs to integrate AI workflows into CRM and ticketing databases."
          };
        }
      case "Governance Readiness":
        if (score >= 70) {
          return {
            explanation: `Rigid control logs and tracking structures are configured, ensuring all automated client operations remain audible.`,
            recommendation: "Configure automated prompt-engineering validation rules and deploy semantic filters to continuously check LLM outputs."
          };
        } else {
          return {
            explanation: `Compliance requirements (${compStr}) are known, but AI-specific controls like audit trails, approval gates, and output validation must be strengthened.`,
            recommendation: "Mandate Human Review workflows for all generated proposal drafts and support responses before external delivery."
          };
        }
      case "Security Readiness":
        if (score >= 70) {
          return {
            explanation: `Strong security postures are active, including SOC2/GDPR compliance frameworks that cover basic data access rights.`,
            recommendation: "Implement private tenant workspace isolations and set up enterprise single-sign-on (SSO) credentials."
          };
        } else {
          return {
            explanation: `Security baseline is operational, but sensitive document handling, regex-based PII scrubbing, and role-based access controls require enforcement before scale.`,
            recommendation: "Integrate automatic pre-processing sanitizers to scrub proprietary figures and customer identifiers before dispatching to external APIs."
          };
        }
      case "Team Readiness":
        if (score >= 70) {
          return {
            explanation: "Consultants and transformation executives display strong agility and are highly prepared to adopt conversational AI copilots.",
            recommendation: "Appoint internal 'AI champions' to host weekly feedback sessions and prioritize next-phase feature requirements."
          };
        } else {
          return {
            explanation: `Teams can highly benefit from AI proposal and support copilots, but formal usage guidelines and onboarding cycles are required for sustainable adoption.`,
            recommendation: "Conduct structured training workshops and define clear guidelines highlighting standard operating protocols for AI outputs."
          };
        }
      case "Business Alignment":
        if (score >= 70) {
          return {
            explanation: `AI opportunities align tightly with high-priority business objectives such as shortening sales cycles and improving margins.`,
            recommendation: "Track clear key performance indicators (KPIs) like average draft generation time to demonstrate strategic ROI."
          };
        } else {
          return {
            explanation: `AI goals are aligned with general priorities (e.g. efficiency or cost reduction), but require concrete mapping to operational bottlenecks.`,
            recommendation: "Establish immediate pilot projects (like proposal copilot MVP) to quickly prove value and secure leadership buy-in."
          };
        }
      default:
        return {
          explanation: "Assessment dimension calculated based on intake signals and industry averages.",
          recommendation: "Continue tracking baseline metrics across discovery sessions."
        };
    }
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

      const demoRes = await fetch(`${API_BASE}/assessments/demo`, {
        method: "POST",
        headers: getAuthHeaders(),
      });
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
      // Fallback local UI mock data if backend offline
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

  // Trigger seeding Apex Consulting instantly on dashboard load
  useEffect(() => {
    if (isLoggedIn) {
      loadClients();
      loadAssessments();
    }
  }, [isLoggedIn, loadAssessments, loadClients]);

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
      { subject: "Data Readiness", A: selectedAssessment.data_readiness },
      { subject: "Process Readiness", A: selectedAssessment.process_readiness },
      { subject: "Integration Readiness", A: selectedAssessment.integration_readiness },
      { subject: "Governance Readiness", A: selectedAssessment.governance_readiness },
      { subject: "Security Readiness", A: selectedAssessment.security_readiness },
      { subject: "Team Readiness", A: selectedAssessment.team_readiness },
      { subject: "Business Alignment", A: selectedAssessment.business_alignment }
    ];
  };

  const getBarData = () => {
    return getRadarData();
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
              Consulting Console
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
                          <td className="py-2.5 text-blue-400 font-bold">{sig.confidence}%</td>
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
                { id: "export", label: "Strategy Asset Generator", icon: Download }
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
                <div className="flex items-center justify-between p-2 bg-slate-950 rounded-lg border border-slate-800">
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
                </div>

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
                  <span>Confidence: <strong className="text-blue-400">{selectedAssessment.confidence_score}%</strong></span>
                  <span>•</span>
                  <span>Impact Index: <strong className="text-indigo-400">High</strong></span>
                  <span>•</span>
                  <span>Readiness Rank: <strong className="text-emerald-400">{int(selectedAssessment.overall_score)}/100</strong></span>
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
                          <span className="text-[10px] text-blue-400 font-bold">{u.confidence}% Confidence</span>
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
                          <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "8px", fontSize: 10 }} />
                          <Bar dataKey="A" fill="#6366f1" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed pt-4 border-t border-slate-800">
                    <strong>Interpretation:</strong> {selectedAssessment.readiness_interpretation}
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
                        const { explanation, recommendation } = getReadinessDimensionExplanation(dim.subject, dim.score);
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
                                      const keys = ["data_readiness", "process_readiness", "integration_readiness", "governance_readiness", "security_readiness", "team_readiness", "business_alignment"];
                                      const avg = Math.round(keys.reduce((acc, k) => acc + int(newAssessment[k as keyof Assessment] as number), 0) / keys.length);
                                      newAssessment.overall_score = avg;
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
                                      const keys = ["data_readiness", "process_readiness", "integration_readiness", "governance_readiness", "security_readiness", "team_readiness", "business_alignment"];
                                      const avg = Math.round(keys.reduce((acc, k) => acc + int(newAssessment[k as keyof Assessment] as number), 0) / keys.length);
                                      newAssessment.overall_score = avg;
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
                            <p className="text-[11px] text-slate-400 leading-relaxed">
                              <strong>Status:</strong> {explanation}
                            </p>
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
