// TypeScript Types for StayChat AI Operations Dashboard

export type MessageRole = "user" | "assistant" | "system";

export interface RetrievedChunk {
  category: string;
  subsection: string;
  score: number;
  content: string;
}

export interface PipelineTelemetry {
  request_id: string;
  session_id: string;
  intent: string;
  language: string;
  latency_ms: number;
  confidence_score: number;
  route: "retrieval" | "bypass" | "unknown";
  guardrail_status: "passed" | "escalate";
  escalation_status: "stable" | "escalated";
  escalation_reason?: string;
  chunks: RetrievedChunk[];
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  telemetry?: PipelineTelemetry;
}

export interface SystemHealth {
  status: "healthy" | "unhealthy";
  faiss: "connected" | "error";
  gemini: "configured" | "error";
  memory: "ready" | "error";
}

export interface AnalyticsSummary {
  totalQueries: number;
  averageConfidence: number;
  escalationCount: number;
  retrievalSuccessRate: number;
  languageDistribution: { name: string; value: number }[];
  intentDistribution: { name: string; value: number }[];
  latencyHistory: { queryIndex: number; latency: number }[];
}

export interface ChatSession {
  id: string;
  title: string;
  date: string;
  messages: Message[];
}
