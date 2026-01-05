"""
Analytics and Threat Processing
Advanced threat analysis with AI-powered agentic reasoning
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import defaultdict, Counter
import json

from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletion

from models import AlertType, AlertSeverity, ThreatInfo
from database import get_db, Alert, ThreatIntelligence
from config import settings
from search_service import ThreatIntelligenceSearch

logger = logging.getLogger(__name__)

class ThreatAnalyzer:
    """Advanced threat analysis with AI-powered agentic reasoning and RAG"""
    
    def __init__(self):
        self.threat_patterns = self._load_threat_patterns()
        self.severity_weights = {
            AlertSeverity.LOW: 0.2,
            AlertSeverity.MEDIUM: 0.5,
            AlertSeverity.HIGH: 0.8,
            AlertSeverity.CRITICAL: 1.0
        }
        self.alert_type_weights = {
            AlertType.NETWORK_ANOMALY: 0.6,
            AlertType.INTRUSION_DETECTION: 0.9,
            AlertType.MALWARE_DETECTION: 1.0,
            AlertType.SUSPICIOUS_BEHAVIOR: 0.7,
            AlertType.DATA_EXFILTRATION: 1.0,
            AlertType.UNAUTHORIZED_ACCESS: 0.9
        }
        
        # Initialize Azure OpenAI client
        self.ai_client = None
        if settings.AI_ENABLED and settings.AZURE_OPENAI_API_KEY:
            try:
                self.ai_client = AsyncAzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
                )
                logger.info("✅ Azure OpenAI client initialized for agentic reasoning")
            except Exception as e:
                logger.warning(f"⚠️ Azure OpenAI initialization failed: {e}. Falling back to deterministic analysis.")
                self.ai_client = None
        else:
            logger.info("ℹ️ AI-powered analysis disabled. Using deterministic algorithms.")
        
        # Initialize Azure AI Search for RAG
        self.search_service = ThreatIntelligenceSearch()
        if self.search_service.search_client:
            logger.info("✅ Azure AI Search initialized for RAG-enhanced analysis")
    
    def _load_threat_patterns(self) -> Dict[str, Any]:
        """Load threat intelligence patterns"""
        # In production, this would load from threat intelligence feeds
        return {
            "malicious_ips": set(),
            "suspicious_domains": set(),
            "attack_signatures": [],
            "behavioral_patterns": {}
        }
    
    async def reason_with_ai(
        self, 
        prompt: str, 
        context: Dict[str, Any], 
        system_role: str = "You are a senior cybersecurity analyst specializing in threat intelligence and incident response."
    ) -> Optional[str]:
        """
        Core AI reasoning method using Azure OpenAI
        
        Args:
            prompt: The question or task for the AI
            context: Relevant data context (alert data, network info, etc.)
            system_role: System message defining the AI's role
            
        Returns:
            AI-generated response or None if AI is unavailable
        """
        if not self.ai_client:
            logger.debug("AI client not available, skipping AI reasoning")
            return None
        
        try:
            # Build messages for the AI
            messages = [
                {"role": "system", "content": system_role},
                {"role": "user", "content": f"{prompt}\n\nContext Data:\n{json.dumps(context, indent=2, default=str)}"}
            ]
            
            # Call Azure OpenAI
            response: ChatCompletion = await self.ai_client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                temperature=settings.AI_MODEL_TEMPERATURE,
                max_tokens=settings.AI_MAX_TOKENS
            )
            
            ai_response = response.choices[0].message.content
            logger.info(f"🤖 AI reasoning completed ({response.usage.total_tokens} tokens)")
            return ai_response
            
        except Exception as e:
            logger.error(f"AI reasoning failed: {e}")
            return None
    
    async def calculate_threat_score(self, alert: Alert) -> float:
        """
        Calculate comprehensive threat score with AI-driven intent analysis
        Uses GPT-4o to understand attack intent and Cyber Kill Chain stage
        """
        try:
            # If AI is available, use agentic reasoning for intent analysis
            if self.ai_client:
                return await self._calculate_threat_score_ai(alert)
            else:
                # Fallback to deterministic scoring
                return await self._calculate_threat_score_deterministic(alert)
                
        except Exception as e:
            logger.error(f"Threat score calculation failed for alert {alert.id}: {e}")
            return 0.5  # Default moderate score
    
    async def _calculate_threat_score_ai(self, alert: Alert) -> float:
        """AI-powered threat scoring with RAG-enhanced context"""
        try:
            # Query similar historical threats for context (RAG)
            similar_threats = []
            if self.search_service.search_client:
                query = f"{alert.alert_type} {alert.title} {alert.description}"
                similar_threats = await self.search_service.search_similar_threats(
                    query=query,
                    alert_type=alert.alert_type,
                    top=3,
                    min_score=0.6
                )
            
            # Prepare context for AI analysis with RAG enhancement
            context = {
                "current_alert": {
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "source": alert.source,
                    "title": alert.title,
                    "description": alert.description,
                    "timestamp": alert.timestamp.isoformat(),
                    "network_context": alert.network_context or {},
                    "raw_data": alert.raw_data or {},
                    "indicators": alert.indicators or []
                },
                "historical_context": similar_threats if similar_threats else "No similar historical threats found"
            }
            
            # Enhanced AI prompt with RAG context
            prompt = """Analyze this security alert and provide a threat assessment.

**IMPORTANT**: Consider the historical context of similar past incidents when making your assessment.

Your analysis should include:
1. **Cyber Kill Chain Stage**: Identify which stage(s) this represents:
   - Reconnaissance
   - Weaponization
   - Delivery
   - Exploitation
   - Installation
   - Command & Control (C2)
   - Actions on Objectives (Exfiltration)

2. **Threat Score**: Rate the threat level from 0.0 to 1.0 based on:
   - Attack sophistication
   - Potential impact
   - Urgency of response needed
   - Evidence strength
   - Pattern matching with historical incidents

3. **Intent Analysis**: What is the attacker likely trying to accomplish?

4. **Confidence**: How confident are you in this assessment (0.0-1.0)?

5. **Historical Insights**: How does this compare to past incidents? (if historical context available)

Respond in JSON format:
{
  "kill_chain_stage": "stage_name",
  "threat_score": 0.85,
  "intent": "description of likely attacker intent",
  "confidence": 0.90,
  "reasoning": "brief explanation"
}"""

            ai_response = await self.reason_with_ai(
                prompt=prompt,
                context=context,
                system_role="You are a senior cybersecurity analyst with expertise in threat intelligence, incident response, and the Cyber Kill Chain framework. Provide concise, actionable analysis."
            )
            
            if ai_response:
                # Parse AI response
                try:
                    # Extract JSON from response (handles markdown code blocks)
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
                    if json_match:
                        ai_analysis = json.loads(json_match.group(1))
                    else:
                        # Try direct JSON parsing
                        ai_analysis = json.loads(ai_response)
                    
                    threat_score = float(ai_analysis.get("threat_score", 0.5))
                    confidence = float(ai_analysis.get("confidence", 0.8))
                    
                    # Weight score by AI confidence
                    final_score = threat_score * confidence
                    
                    logger.info(
                        f"🤖 RAG-Enhanced AI Analysis for alert {alert.id}: "
                        f"Score={threat_score:.3f}, Confidence={confidence:.3f}, "
                        f"Stage={ai_analysis.get('kill_chain_stage', 'unknown')}, "
                        f"Historical Context: {len(similar_threats)} similar threats"
                    )
                    
                    # Store AI analysis in alert metadata (optional)
                    alert.ai_analysis = ai_analysis
                    
                    return max(0.0, min(1.0, final_score))
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse AI response: {e}. Falling back to deterministic scoring.")
            
            # Fallback if AI response is invalid
            return await self._calculate_threat_score_deterministic(alert)
            
        except Exception as e:
            logger.error(f"AI threat scoring failed: {e}")
            return await self._calculate_threat_score_deterministic(alert)
    
    async def _calculate_threat_score_deterministic(self, alert: Alert) -> float:
        """Fallback deterministic threat scoring (original algorithm)"""
        base_score = 0.0
        
        # Base score from severity and type
        severity_score = self.severity_weights.get(AlertSeverity(alert.severity), 0.5)
        type_score = self.alert_type_weights.get(AlertType(alert.alert_type), 0.5)
        base_score = (severity_score + type_score) / 2
        
        # Contextual scoring
        context_score = await self._calculate_context_score(alert)
        
        # Historical scoring
        historical_score = await self._calculate_historical_score(alert)
        
        # Indicator scoring
        indicator_score = await self._calculate_indicator_score(alert)
        
        # Combine scores with weights
        final_score = (
            base_score * 0.3 +
            context_score * 0.3 +
            historical_score * 0.2 +
            indicator_score * 0.2
        )
        
        # Normalize to 0-1 range
        final_score = max(0.0, min(1.0, final_score))
        
        logger.info(f"Calculated deterministic threat score {final_score:.3f} for alert {alert.id}")
        return final_score
    
    async def _calculate_context_score(self, alert: Alert) -> float:
        """Calculate score based on alert context"""
        score = 0.0
        
        try:
            if alert.network_context:
                # Check for suspicious network patterns
                network_data = alert.network_context
                
                # High frequency of connections
                if network_data.get("connection_count", 0) > 100:
                    score += 0.3
                
                # Unusual ports
                unusual_ports = {22, 23, 135, 139, 445, 1433, 3389}
                if network_data.get("dest_port") in unusual_ports:
                    score += 0.2
                
                # External connections
                if network_data.get("external_connection", False):
                    score += 0.2
            
            # Check raw data for additional indicators
            if alert.raw_data:
                raw = alert.raw_data
                
                # Large data transfers
                if raw.get("bytes_transferred", 0) > 1000000:  # > 1MB
                    score += 0.2
                
                # Failed authentication attempts
                if "failed_auth" in raw and raw["failed_auth"] > 5:
                    score += 0.3
        
        except Exception as e:
            logger.warning(f"Context scoring failed for alert {alert.id}: {e}")
        
        return min(1.0, score)
    
    async def _calculate_historical_score(self, alert: Alert) -> float:
        """Calculate score based on historical alert patterns"""
        try:
            async with get_db() as db:
                # Look for similar alerts in the last 24 hours
                time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
                
                similar_alerts = await db.execute(
                    "SELECT COUNT(*) FROM alerts WHERE alert_type = %s AND timestamp > %s",
                    (alert.alert_type, time_threshold)
                )
                count = similar_alerts.scalar() or 0
                
                # Higher frequency = higher score
                if count > 10:
                    return 0.8
                elif count > 5:
                    return 0.6
                elif count > 2:
                    return 0.4
                else:
                    return 0.2
                    
        except Exception as e:
            logger.warning(f"Historical scoring failed for alert {alert.id}: {e}")
            return 0.3
    
    async def _calculate_indicator_score(self, alert: Alert) -> float:
        """Calculate score based on threat intelligence indicators"""
        score = 0.0
        
        try:
            if alert.indicators:
                for indicator in alert.indicators:
                    # Check against known threat indicators
                    if indicator in self.threat_patterns["malicious_ips"]:
                        score += 0.4
                    elif indicator in self.threat_patterns["suspicious_domains"]:
                        score += 0.3
                    
                    # Pattern matching for suspicious indicators
                    if self._matches_attack_pattern(indicator):
                        score += 0.2
        
        except Exception as e:
            logger.warning(f"Indicator scoring failed for alert {alert.id}: {e}")
        
        return min(1.0, score)
    
    def _matches_attack_pattern(self, indicator: str) -> bool:
        """Check if indicator matches known attack patterns"""
        # Simplified pattern matching - would be more sophisticated in production
        suspicious_patterns = [
            r'.*\.exe$',  # Executable files
            r'.*\.(php|jsp|asp).*\?.*',  # Web shell patterns
            r'.*[\<\>].*',  # Script injection attempts
        ]
        
        import re
        for pattern in suspicious_patterns:
            if re.match(pattern, indicator, re.IGNORECASE):
                return True
        return False
    
    async def analyze_threats(
        self,
        time_window: int,
        threat_types: List[AlertType] = None,
        severity_filter: AlertSeverity = None
    ) -> Dict[str, Any]:
        """
        Comprehensive threat analysis with AI-powered insights
        Includes adaptive threshold recommendations for Sentry configuration
        """
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(seconds=time_window)
            
            async with get_db() as db:
                # Build query filters
                filters = ["timestamp >= %s AND timestamp <= %s"]
                params = [start_time, end_time]
                
                if threat_types:
                    filters.append(f"alert_type IN ({','.join(['%s'] * len(threat_types))})")
                    params.extend([t.value for t in threat_types])
                
                if severity_filter:
                    filters.append("severity = %s")
                    params.append(severity_filter.value)
                
                # Get alerts for analysis
                query = f"SELECT * FROM alerts WHERE {' AND '.join(filters)}"
                result = await db.execute(query, params)
                alerts = result.fetchall()
                
                # Analyze threats
                threats_detected = []
                correlations = []
                
                # Group alerts by patterns
                threat_groups = self._group_threats(alerts)
                
                for group_id, group_alerts in threat_groups.items():
                    threat_info = await self._analyze_threat_group(group_alerts)
                    if threat_info:
                        threats_detected.append(threat_info)
                
                # Calculate overall risk score
                risk_score = self._calculate_overall_risk(threats_detected)
                
                # Generate AI-powered recommendations
                recommendations = await self._generate_recommendations_ai(threats_detected) if self.ai_client else self._generate_recommendations_deterministic(threats_detected)
                
                # Generate adaptive threshold recommendation
                threshold_recommendation = await self._recommend_threshold_adjustment(
                    alerts=alerts,
                    threats=threats_detected,
                    time_window=time_window
                )
                
                return {
                    "threats": threats_detected,
                    "risk_score": risk_score,
                    "recommendations": recommendations,
                    "correlations": correlations,
                    "threshold_recommendation": threshold_recommendation,
                    "ai_enhanced": self.ai_client is not None
                }
                
        except Exception as e:
            logger.error(f"Threat analysis failed: {e}")
            return {
                "threats": [],
                "risk_score": 0.0,
                "recommendations": [],
                "correlations": [],
                "threshold_recommendation": None,
                "ai_enhanced": False
            }
    
    async def _recommend_threshold_adjustment(
        self,
        alerts: List[Alert],
        threats: List[ThreatInfo],
        time_window: int
    ) -> Dict[str, Any]:
        """
        AI-powered adaptive threshold recommendation for KitNET Sentry
        Analyzes alert patterns to suggest optimal detection sensitivity
        """
        if not self.ai_client:
            return self._recommend_threshold_deterministic(alerts, threats, time_window)
        
        try:
            # Prepare metrics for AI analysis
            total_alerts = len(alerts)
            alerts_per_hour = (total_alerts / time_window) * 3600
            
            severity_distribution = Counter(a.severity for a in alerts)
            alert_type_distribution = Counter(a.alert_type for a in alerts)
            
            high_severity_ratio = (
                severity_distribution.get(AlertSeverity.HIGH.value, 0) +
                severity_distribution.get(AlertSeverity.CRITICAL.value, 0)
            ) / max(total_alerts, 1)
            
            context = {
                "time_window_hours": time_window / 3600,
                "total_alerts": total_alerts,
                "alerts_per_hour": round(alerts_per_hour, 2),
                "severity_distribution": dict(severity_distribution),
                "alert_type_distribution": dict(alert_type_distribution),
                "high_severity_ratio": round(high_severity_ratio, 3),
                "threats_detected": len(threats),
                "current_threshold": 0.95
            }
            
            prompt = """Analyze the current alert patterns from the Cardea Sentry system and recommend if the KITNET_THRESHOLD should be adjusted.

Current threshold is 0.95 (alerts triggered when anomaly score ≥ 0.95).

Consider:
- Alert volume and frequency
- Ratio of high-severity alerts (potential true positives)
- Threat detection effectiveness
- Risk of alert fatigue vs. risk of missed threats

Provide recommendation in JSON format:
{
  "action": "LOWER|MAINTAIN|RAISE",
  "recommended_value": 0.93,
  "reasoning": "brief explanation",
  "confidence": 0.85,
  "expected_impact": "what will change"
}

Guidelines:
- LOWER (0.90-0.94): If missing critical threats or low alert volume with high severity ratio
- MAINTAIN (0.95): If current balance is optimal
- RAISE (0.96-0.98): If too many false positives or alert fatigue evident"""

            ai_response = await self.reason_with_ai(
                prompt=prompt,
                context=context,
                system_role="You are a cybersecurity engineer specializing in intrusion detection system tuning and anomaly detection optimization."
            )
            
            if ai_response:
                try:
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
                    if json_match:
                        recommendation = json.loads(json_match.group(1))
                    else:
                        recommendation = json.loads(ai_response)
                    
                    logger.info(
                        f"🎚️ AI Threshold Recommendation: {recommendation['action']} "
                        f"to {recommendation.get('recommended_value', 0.95)}"
                    )
                    
                    return {
                        "action": recommendation.get("action", "MAINTAIN"),
                        "recommended_value": recommendation.get("recommended_value", 0.95),
                        "current_value": 0.95,
                        "reasoning": recommendation.get("reasoning", ""),
                        "confidence": recommendation.get("confidence", 0.5),
                        "expected_impact": recommendation.get("expected_impact", ""),
                        "ai_generated": True
                    }
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse AI threshold recommendation: {e}")
            
        except Exception as e:
            logger.error(f"AI threshold recommendation failed: {e}")
        
        return self._recommend_threshold_deterministic(alerts, threats, time_window)
    
    def _recommend_threshold_deterministic(
        self,
        alerts: List[Alert],
        threats: List[ThreatInfo],
        time_window: int
    ) -> Dict[str, Any]:
        """Deterministic threshold recommendation based on heuristics"""
        total_alerts = len(alerts)
        alerts_per_hour = (total_alerts / time_window) * 3600 if time_window > 0 else 0
        
        high_severity_count = sum(
            1 for a in alerts 
            if a.severity in [AlertSeverity.HIGH.value, AlertSeverity.CRITICAL.value]
        )
        high_severity_ratio = high_severity_count / max(total_alerts, 1)
        
        # Decision logic
        if alerts_per_hour < 1 and high_severity_ratio > 0.5:
            action = "LOWER"
            recommended_value = 0.93
            reasoning = "Low alert volume but high severity ratio suggests we may be missing threats"
        elif alerts_per_hour > 20 and high_severity_ratio < 0.1:
            action = "RAISE"
            recommended_value = 0.97
            reasoning = "High alert volume with low severity ratio indicates potential alert fatigue"
        else:
            action = "MAINTAIN"
            recommended_value = 0.95
            reasoning = "Current threshold appears balanced for the threat landscape"
        
        return {
            "action": action,
            "recommended_value": recommended_value,
            "current_value": 0.95,
            "reasoning": reasoning,
            "confidence": 0.7,
            "expected_impact": f"Alert volume may {'increase' if action == 'LOWER' else 'decrease' if action == 'RAISE' else 'remain stable'}",
            "ai_generated": False
        }
    
    def _group_threats(self, alerts: List[Alert]) -> Dict[str, List[Alert]]:
        """Group related alerts into threat clusters"""
        groups = defaultdict(list)
        
        for alert in alerts:
            # Simple grouping by alert type and source
            group_key = f"{alert.alert_type}_{alert.source}"
            groups[group_key].append(alert)
        
        return groups
    
    async def _analyze_threat_group(self, alerts: List[Alert]) -> Optional[ThreatInfo]:
        """Analyze a group of related alerts"""
        if not alerts:
            return None
        
        try:
            # Calculate group statistics
            severities = [a.severity for a in alerts]
            most_severe = max(severities, key=lambda s: self.severity_weights.get(AlertSeverity(s), 0))
            
            # Aggregate indicators
            all_indicators = []
            for alert in alerts:
                if alert.indicators:
                    all_indicators.extend(alert.indicators)
            
            # Calculate confidence based on alert count and consistency
            confidence_score = min(1.0, len(alerts) * 0.1 + 0.3)
            
            return ThreatInfo(
                threat_id=f"threat_{alerts[0].alert_type}_{int(datetime.now().timestamp())}",
                threat_type=AlertType(alerts[0].alert_type),
                severity=AlertSeverity(most_severe),
                confidence_score=confidence_score,
                first_seen=min(a.timestamp for a in alerts),
                last_seen=max(a.timestamp for a in alerts),
                indicators=list(set(all_indicators)),
                affected_assets=[f"{a.source}_{a.id}" for a in alerts]
            )
            
        except Exception as e:
            logger.error(f"Threat group analysis failed: {e}")
            return None
    
    def _calculate_overall_risk(self, threats: List[ThreatInfo]) -> float:
        """Calculate overall risk score from detected threats"""
        if not threats:
            return 0.0
        
        # Weight threats by severity and confidence
        total_risk = 0.0
        for threat in threats:
            severity_weight = self.severity_weights.get(threat.severity, 0.5)
            risk_contribution = severity_weight * threat.confidence_score
            total_risk += risk_contribution
        
        # Normalize by number of threats with diminishing returns
        risk_score = total_risk / (1 + len(threats) * 0.1)
        return min(1.0, risk_score)
    
    def _generate_recommendations(self, threats: List[ThreatInfo]) -> List[str]:
        """
        Generate AI-powered security recommendations
        Fallback to deterministic recommendations if AI unavailable
        """
        if self.ai_client and threats:
            # Use async wrapper for AI recommendations
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self._generate_recommendations_ai(threats))
            except Exception as e:
                logger.warning(f"AI recommendations failed: {e}. Using deterministic fallback.")
        
        return self._generate_recommendations_deterministic(threats)
    
    async def _generate_recommendations_ai(self, threats: List[ThreatInfo]) -> List[str]:
        """AI-powered recommendations with adaptive threshold suggestions"""
        try:
            # Prepare threat summary for AI
            threat_summary = []
            for threat in threats:
                threat_summary.append({
                    "threat_type": threat.threat_type.value,
                    "severity": threat.severity.value,
                    "confidence": threat.confidence_score,
                    "first_seen": threat.first_seen.isoformat(),
                    "last_seen": threat.last_seen.isoformat(),
                    "indicators": threat.indicators[:5],  # Limit for token efficiency
                    "affected_assets": len(threat.affected_assets)
                })
            
            context = {
                "total_threats": len(threats),
                "threat_details": threat_summary,
                "time_window": "Recent analysis period",
                "high_severity_count": sum(1 for t in threats if t.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL])
            }
            
            prompt = """As a cybersecurity expert, analyze these detected threats and provide actionable recommendations for a non-technical business owner.

Structure your response EXACTLY in three sections:

## What Happened
[2-3 sentences explaining the security events in plain language, avoiding technical jargon]

## Why It Matters
[2-3 sentences explaining the business impact and risk - what could happen if not addressed]

## What To Do Now
[3-5 numbered action items in priority order, each starting with an action verb]

ADDITIONAL ANALYSIS:
- **KITNET Threshold Adjustment**: Based on the current threat volume and pattern, should the Sentry's KITNET_THRESHOLD (currently 0.95) be adjusted? Recommend LOWER (more sensitive), MAINTAIN (current is good), or RAISE (reduce false positives). Provide specific value and brief reasoning.

Use clear, direct language suitable for a small business owner without cybersecurity expertise."""

            ai_response = await self.reason_with_ai(
                prompt=prompt,
                context=context,
                system_role="You are a senior cybersecurity consultant who specializes in translating technical threats into business language for SME owners. Be concise, actionable, and reassuring while conveying urgency appropriately."
            )
            
            if ai_response:
                # Parse the response into structured format
                recommendations = []
                
                # Extract sections
                sections = {
                    "what_happened": "",
                    "why_it_matters": "",
                    "what_to_do": "",
                    "threshold_adjustment": ""
                }
                
                current_section = None
                for line in ai_response.split('\n'):
                    line = line.strip()
                    if '## What Happened' in line or '**What Happened**' in line:
                        current_section = "what_happened"
                    elif '## Why It Matters' in line or '**Why It Matters**' in line:
                        current_section = "why_it_matters"
                    elif '## What To Do Now' in line or '**What To Do Now**' in line:
                        current_section = "what_to_do"
                    elif 'KITNET Threshold' in line or 'Threshold Adjustment' in line:
                        current_section = "threshold_adjustment"
                    elif current_section and line:
                        sections[current_section] += line + " "
                
                # Format as structured recommendations
                if sections["what_happened"]:
                    recommendations.append(f"📋 WHAT HAPPENED: {sections['what_happened'].strip()}")
                if sections["why_it_matters"]:
                    recommendations.append(f"⚠️ WHY IT MATTERS: {sections['why_it_matters'].strip()}")
                if sections["what_to_do"]:
                    recommendations.append(f"✅ WHAT TO DO NOW: {sections['what_to_do'].strip()}")
                if sections["threshold_adjustment"]:
                    recommendations.append(f"🎚️ SENTRY ADJUSTMENT: {sections['threshold_adjustment'].strip()}")
                
                # If parsing failed, use raw response
                if not recommendations:
                    recommendations.append(ai_response)
                
                logger.info(f"🤖 Generated {len(recommendations)} AI-powered recommendations")
                return recommendations
                
        except Exception as e:
            logger.error(f"AI recommendation generation failed: {e}")
        
        # Fallback to deterministic
        return self._generate_recommendations_deterministic(threats)
    
    def _generate_recommendations_deterministic(self, threats: List[ThreatInfo]) -> List[str]:
        """Deterministic security recommendations (original algorithm)"""
        recommendations = []
        
        threat_types = [t.threat_type for t in threats]
        
        if AlertType.MALWARE_DETECTION in threat_types:
            recommendations.append("Perform full system malware scan and isolate affected systems")
        
        if AlertType.INTRUSION_DETECTION in threat_types:
            recommendations.append("Review firewall rules and network access controls")
        
        if AlertType.DATA_EXFILTRATION in threat_types:
            recommendations.append("Investigate data access logs and implement DLP controls")
        
        if AlertType.UNAUTHORIZED_ACCESS in threat_types:
            recommendations.append("Review user access permissions and authentication logs")
        
        # General recommendations
        if len(threats) > 5:
            recommendations.append("Consider raising security alert level due to high threat volume")
        
        high_severity_count = sum(1 for t in threats if t.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL])
        if high_severity_count > 2:
            recommendations.append("Immediate security team escalation recommended")
        
        return recommendations

class AlertCorrelator:
    """Alert correlation and relationship detection"""
    
    def __init__(self):
        self.correlation_algorithms = {
            "temporal": self._temporal_correlation,
            "network": self._network_correlation,
            "behavioral": self._behavioral_correlation
        }
    
    async def find_correlations(self, alert: Alert) -> List[Dict[str, Any]]:
        """Find correlations for a given alert"""
        correlations = []
        
        try:
            for correlation_type, algorithm in self.correlation_algorithms.items():
                related_alerts = await algorithm(alert)
                for related_alert, score in related_alerts:
                    correlations.append({
                        "type": correlation_type,
                        "related_alert_id": related_alert.id,
                        "correlation_score": score,
                        "reason": f"{correlation_type} correlation detected"
                    })
        
        except Exception as e:
            logger.error(f"Correlation analysis failed for alert {alert.id}: {e}")
        
        return correlations
    
    async def _temporal_correlation(self, alert: Alert) -> List[Tuple[Alert, float]]:
        """Find temporally correlated alerts"""
        correlations = []
        
        try:
            # Look for alerts within ±30 minutes
            time_window = timedelta(minutes=30)
            start_time = alert.timestamp - time_window
            end_time = alert.timestamp + time_window
            
            async with get_db() as db:
                result = await db.execute(
                    "SELECT * FROM alerts WHERE timestamp BETWEEN %s AND %s AND id != %s",
                    (start_time, end_time, alert.id)
                )
                nearby_alerts = result.fetchall()
                
                for nearby_alert in nearby_alerts:
                    # Calculate temporal correlation score
                    time_diff = abs((alert.timestamp - nearby_alert.timestamp).total_seconds())
                    score = max(0.0, 1.0 - (time_diff / 1800))  # 30 minutes = 0 score
                    
                    if score > 0.5:  # Threshold for correlation
                        correlations.append((nearby_alert, score))
        
        except Exception as e:
            logger.warning(f"Temporal correlation failed: {e}")
        
        return correlations
    
    async def _network_correlation(self, alert: Alert) -> List[Tuple[Alert, float]]:
        """Find network-based correlations"""
        correlations = []
        
        try:
            if not alert.network_context:
                return correlations
            
            source_ip = alert.network_context.get("source_ip")
            dest_ip = alert.network_context.get("dest_ip")
            
            if source_ip or dest_ip:
                async with get_db() as db:
                    # Find alerts with same IP addresses
                    result = await db.execute(
                        """
                        SELECT * FROM alerts 
                        WHERE id != %s AND (
                            network_context->>'source_ip' = %s OR
                            network_context->>'dest_ip' = %s OR
                            network_context->>'source_ip' = %s OR
                            network_context->>'dest_ip' = %s
                        )
                        """,
                        (alert.id, source_ip, dest_ip, dest_ip, source_ip)
                    )
                    related_alerts = result.fetchall()
                    
                    for related_alert in related_alerts:
                        # Calculate network correlation score
                        score = 0.8  # High score for IP matches
                        correlations.append((related_alert, score))
        
        except Exception as e:
            logger.warning(f"Network correlation failed: {e}")
        
        return correlations
    
    async def _behavioral_correlation(self, alert: Alert) -> List[Tuple[Alert, float]]:
        """Find behavioral pattern correlations"""
        correlations = []
        
        try:
            # Look for similar alert types from same source
            async with get_db() as db:
                result = await db.execute(
                    "SELECT * FROM alerts WHERE alert_type = %s AND source = %s AND id != %s",
                    (alert.alert_type, alert.source, alert.id)
                )
                similar_alerts = result.fetchall()
                
                for similar_alert in similar_alerts:
                    # Calculate behavioral correlation score based on similarity
                    score = 0.6  # Moderate score for same type/source
                    
                    # Increase score if similar severity
                    if similar_alert.severity == alert.severity:
                        score += 0.2
                    
                    correlations.append((similar_alert, score))
        
        except Exception as e:
            logger.warning(f"Behavioral correlation failed: {e}")
        
        return correlations
    
    async def index_threat_for_rag(self, alert: Alert, threat_score: float, ai_analysis: Optional[Dict] = None) -> bool:
        """
        Index analyzed threat into Azure Search for future RAG queries
        
        Args:
            alert: The alert that was analyzed
            threat_score: Calculated threat score
            ai_analysis: Optional AI analysis results
            
        Returns:
            True if successfully indexed, False otherwise
        """
        if not self.search_service.search_client:
            logger.debug("Search service not available, skipping indexing")
            return False
        
        try:
            # Prepare threat document
            threat_data = {
                "threat_id": f"threat_{alert.id}_{int(alert.timestamp.timestamp())}",
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "resolution": "",  # To be filled in when threat is resolved
                "indicators": alert.indicators or [],
                "attack_patterns": [alert.alert_type],
                "threat_score": threat_score,
                "confidence_score": ai_analysis.get("confidence", 0.8) if ai_analysis else 0.7,
                "first_seen": alert.timestamp,
                "last_seen": alert.timestamp,
                "kill_chain_stage": ai_analysis.get("kill_chain_stage", "Unknown") if ai_analysis else "Unknown",
                "network_context": alert.network_context or {},
                "occurrences": 1,
            }
            
            # Index the threat
            success = await self.search_service.index_threat(threat_data)
            
            if success:
                logger.info(f"✅ Indexed threat {threat_data['threat_id']} for RAG")
            else:
                logger.warning(f"Failed to index threat {threat_data['threat_id']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error indexing threat for RAG: {e}")
            return False
