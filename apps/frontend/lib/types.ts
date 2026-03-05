export type RiskLevel = "Low" | "Medium" | "High" | "Critical";

export interface LogEntry {
  level: string;
  message: string;
  source: string;
}

export interface RiskBreakdown {
  entropy_factor: number;
  anomaly_factor: number;
  heuristic_penalty: number;
  raw_total: number;
}

export interface EntryAnalysisReport {
  id: string;
  source: string;
  level: string;
  message: string;
  entropy: number;
  is_anomaly: boolean;
  has_sensitive_data: boolean;
  sensitive_data_tags: string[];
  has_sqli: boolean;
  sqli_tags: string[];
  has_critical_pattern: boolean;
  critical_pattern_tags: string[];
  risk_score: number;
  risk_level: RiskLevel;
  risk_breakdown: RiskBreakdown;
}

export interface ForensicAnalysisReport {
  analyzed_at: string;
  total_entries: number;
  mean_entropy: number;
  anomaly_count: number;
  anomaly_indices: number[];
  sensitive_entry_count: number;
  sqli_entry_count: number;
  critical_pattern_count: number;
  overall_risk_score: number;
  overall_risk_level: RiskLevel;
  overall_risk_breakdown: RiskBreakdown;
  entries: EntryAnalysisReport[];
}

export interface AnalysisResultSummary {
  id: string;
  analyzed_at: string;
  total_entries: number;
  overall_risk_score: number;
  overall_risk_level: RiskLevel;
  anomaly_count: number;
  sensitive_entry_count: number;
  sqli_entry_count: number;
  critical_pattern_count: number;
  mean_entropy: number;
}
