// API and App Configuration
export const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || "http://localhost:8000";
export const SENTRY_URL = import.meta.env.VITE_SENTRY_URL || "http://localhost:8001";

// Severity styling configuration
export const severityConfig = {
  critical: { color: "text-red-500", bg: "bg-red-950/30 border-red-900/50" },
  high: { color: "text-orange-500", bg: "bg-orange-950/30 border-orange-900/50" },
  medium: { color: "text-yellow-500", bg: "bg-yellow-950/30 border-yellow-900/50" },
  low: { color: "text-cyan-500", bg: "bg-cyan-950/30 border-cyan-900/50" },
} as const;

export type SeverityLevel = keyof typeof severityConfig;
