export interface Alert {
    id: number;
    source: string;
    alert_type: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    title: string;
    description: string;
    timestamp: string;
    threat_score?: number;
    raw_data?: Record<string, any>;
  }

  export interface ActionButton {
    id: string;
    label: string;
    action_type: 'block_ip' | 'allow_ip' | 'lockdown' | 'monitor' | 'dismiss' | 'expand';
    severity: 'danger' | 'warning' | 'info' | 'success';
    target?: string;
    description: string;
  }

  export interface AIInsight {
    // New conversational format
    greeting: string;
    status_emoji: string;
    headline: string;
    story: string;
    actions_taken: string[];
    decisions: ActionButton[];
    technical_summary?: string;
    confidence: number;
    generated_at?: string;
    ai_powered: boolean;
    
    // Legacy fields for backward compatibility
    summary?: string;
    what_happened?: string;
    why_it_matters?: string;
    recommended_actions?: string[];
  }
  
  export interface AnalyticsResponse {
    total_alerts: number;
    risk_score: number;
    alerts: Alert[];
    // Extended fields from Oracle backend
    time_range?: string;
    alerts_by_severity?: Record<string, number>;
    alerts_by_type?: Record<string, number>;
    top_threats?: ThreatInfo[];
    trend_data?: Record<string, any>[];
    ai_insight?: AIInsight;
    generated_at?: string;
  }

  export interface ThreatInfo {
    threat_id: string;
    threat_type: string;
    severity: string;
    confidence_score: number;
    first_seen: string;
    last_seen: string;
    indicators: string[];
    affected_assets: string[];
  }

  export interface FlowData {
    nodes: Array<{
      id: string;
      type: string;
      data: { label: string; status?: string };
      position: { x: number; y: number };
    }>;
    edges: Array<{
      id: string;
      source: string;
      target: string;
      animated?: boolean;
    }>;
  }