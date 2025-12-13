"""
Impact Report Service for BuildTrace AI

Generates AI-powered cost and schedule impact reports from detected changes.
"""

import json
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed. Impact reports will use fallback data.")


class ImpactReportService:
    """Generate AI-powered cost and schedule impact reports from detected changes."""
    
    def __init__(self):
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')
            else:
                self.client = None
                logger.warning("OPENAI_API_KEY not set. Impact reports will use fallback data.")
        else:
            self.client = None
    
    def generate_cost_impact(
        self, 
        job_id: str, 
        changes_summary: str, 
        categories: Dict, 
        kpis: Dict
    ) -> Dict:
        """
        Generate cost impact report from detected changes.
        
        Args:
            job_id: The job ID
            changes_summary: Summary of all detected changes
            categories: Change categories (MEP, Structural, etc.)
            kpis: KPIs (added, modified, removed counts)
            
        Returns:
            Cost impact data matching CostImpactData interface
        """
        if not self.client:
            logger.warning("OpenAI client not available, returning fallback cost data")
            return self._get_fallback_cost_data(categories, kpis)
        
        system_prompt = """You are an expert construction cost estimator at a general contractor company with 20+ years of experience in:
- Construction cost estimation and budget planning
- Material pricing and labor rates
- Change order cost analysis
- Regional cost variations (US markets)
- Contingency and risk assessment

You have access to current market rates and industry standards. Always provide realistic cost ranges based on 2024-2025 market conditions.
Use your built-in web search to get current pricing information when needed."""

        user_prompt = f"""Based on the following detected changes from the drawing comparison, generate a detailed cost impact report.

## Detected Changes:
{changes_summary}

## Drawing Categories Affected:
{json.dumps(categories, indent=2)}

## Change Counts:
- Added: {kpis.get('added', 0)}
- Modified: {kpis.get('modified', 0)}  
- Removed: {kpis.get('removed', 0)}

Please provide a comprehensive cost estimate in the following JSON format:

{{
  "categories": [
    {{
      "name": "Category Name (e.g., Building Modifications, Site & Environmental, Professional Services, MEP Systems)",
      "icon": "emoji icon (🏗️, 🌿, 📋, ⚡, etc.)",
      "items": [
        {{
          "item": "Line item name",
          "description": "Brief description of work",
          "costRange": "$X,XXX – $XX,XXX"
        }}
      ]
    }}
  ],
  "subtotal": "$XXX,XXX – $XXX,XXX",
  "contingency": "$XX,XXX – $XX,XXX",
  "contingencyPercent": 10,
  "totalEstimate": "$XXX,XXX – $XXX,XXX",
  "ballparkTotal": "$XXX,XXX – $XXX,XXX",
  "importantNotes": "Key disclaimers and assumptions",
  "nextSteps": "Recommended actions for the project team"
}}

Guidelines:
1. Group costs into logical categories (Building Modifications, Site Work, MEP, Professional Services, etc.)
2. Provide realistic cost RANGES (low-high) for each line item based on the actual changes detected
3. Include 10% contingency for unforeseen conditions
4. Consider labor, materials, equipment, and coordination costs
5. Note any assumptions about scope or conditions
6. Suggest next steps for refining the estimate
7. Base estimates on the ACTUAL changes detected, not generic assumptions

Respond ONLY with valid JSON matching the format above."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_completion_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Generated cost impact report for job {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate cost impact: {e}")
            return self._get_fallback_cost_data(categories, kpis)
    
    def generate_schedule_impact(
        self, 
        job_id: str, 
        changes_summary: str, 
        categories: Dict, 
        kpis: Dict
    ) -> Dict:
        """
        Generate schedule impact report from detected changes.
        
        Args:
            job_id: The job ID
            changes_summary: Summary of all detected changes
            categories: Change categories (MEP, Structural, etc.)
            kpis: KPIs (added, modified, removed counts)
            
        Returns:
            Schedule impact data matching ScheduleImpactData interface
        """
        if not self.client:
            logger.warning("OpenAI client not available, returning fallback schedule data")
            return self._get_fallback_schedule_data(categories, kpis)
        
        system_prompt = """You are an expert construction scheduler and project manager with 20+ years of experience in:
- Critical path method (CPM) scheduling
- Construction sequencing and phasing
- Lead time analysis for materials and equipment
- Permit and approval timelines
- Risk assessment and schedule contingency

You understand typical construction durations, lead times, and the interdependencies between trades.
Use your built-in web search to get current lead times and industry benchmarks when needed."""

        user_prompt = f"""Based on the following detected changes from the drawing comparison, generate a detailed schedule impact analysis.

## Detected Changes:
{changes_summary}

## Drawing Categories Affected:
{json.dumps(categories, indent=2)}

## Change Counts:
- Added: {kpis.get('added', 0)}
- Modified: {kpis.get('modified', 0)}  
- Removed: {kpis.get('removed', 0)}

Please provide a comprehensive schedule impact analysis in the following JSON format:

{{
  "criticalPathItems": [
    {{
      "item": "Activity or procurement item",
      "duration": "X–Y weeks",
      "note": "Why this is critical and any dependencies"
    }}
  ],
  "overlapSummary": "Narrative explaining how activities can be parallelized vs. must be sequential, and the difference in total duration",
  "scenarios": [
    {{
      "name": "Best-case (parallelized)",
      "description": "What conditions lead to this outcome",
      "impact": "+X months",
      "probability": 25,
      "color": "green"
    }},
    {{
      "name": "Typical-case",
      "description": "Most likely scenario with some delays",
      "impact": "+X months",
      "probability": 50,
      "color": "yellow"
    }},
    {{
      "name": "Worst-case (serial)",
      "description": "If everything goes sequentially with delays",
      "impact": "+X–Y months",
      "probability": 25,
      "color": "red"
    }}
  ],
  "bottomLine": "Executive summary of the key schedule drivers and recommendations to minimize delay"
}}

Guidelines:
1. Identify long-lead items (equipment, permits, specialty materials) based on the ACTUAL changes detected
2. Consider trade sequencing and dependencies
3. Account for design revision cycles and re-submittals
4. Include permit and inspection timelines
5. Provide realistic probability percentages that sum to 100%
6. Focus on actionable recommendations to compress the schedule
7. Base the analysis on the ACTUAL changes detected, not generic assumptions

Respond ONLY with valid JSON matching the format above."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_completion_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Generated schedule impact report for job {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate schedule impact: {e}")
            return self._get_fallback_schedule_data(categories, kpis)
    
    def _get_fallback_cost_data(self, categories: Dict, kpis: Dict) -> Dict:
        """Return fallback cost data when AI is unavailable."""
        total_changes = kpis.get('added', 0) + kpis.get('modified', 0) + kpis.get('removed', 0)
        
        # Generate basic cost items based on categories
        cost_categories = []
        
        if categories.get('Structural', 0) > 0 or categories.get('Concrete', 0) > 0:
            cost_categories.append({
                "name": "Structural Modifications",
                "icon": "🏗️",
                "items": [
                    {"item": "Structural Changes", "description": "Based on detected modifications", "costRange": "$15,000 – $50,000"}
                ]
            })
        
        if categories.get('MEP', 0) > 0 or categories.get('Electrical', 0) > 0:
            cost_categories.append({
                "name": "MEP Systems",
                "icon": "⚡",
                "items": [
                    {"item": "MEP Modifications", "description": "Mechanical, electrical, plumbing changes", "costRange": "$10,000 – $35,000"}
                ]
            })
        
        if categories.get('Architectural', 0) > 0:
            cost_categories.append({
                "name": "Architectural Changes",
                "icon": "🏠",
                "items": [
                    {"item": "Architectural Modifications", "description": "Layout and finish changes", "costRange": "$8,000 – $25,000"}
                ]
            })
        
        # Add professional services
        cost_categories.append({
            "name": "Professional Services",
            "icon": "📋",
            "items": [
                {"item": "A/E Revision Hours", "description": "Design coordination", "costRange": "$5,000 – $15,000"},
                {"item": "Permit Updates", "description": "Review and filing fees", "costRange": "$2,000 – $8,000"}
            ]
        })
        
        return {
            "categories": cost_categories,
            "subtotal": "$40,000 – $133,000",
            "contingency": "$4,000 – $13,300",
            "contingencyPercent": 10,
            "totalEstimate": "$44,000 – $146,300",
            "ballparkTotal": "$45,000 – $150,000",
            "importantNotes": "This is a preliminary estimate based on detected changes. Actual costs may vary based on site conditions, material availability, and contractor pricing. AI-generated detailed estimate unavailable.",
            "nextSteps": "Request detailed bids from trade partners to refine each line item."
        }
    
    def _get_fallback_schedule_data(self, categories: Dict, kpis: Dict) -> Dict:
        """Return fallback schedule data when AI is unavailable."""
        total_changes = kpis.get('added', 0) + kpis.get('modified', 0) + kpis.get('removed', 0)
        
        critical_items = []
        
        if categories.get('Structural', 0) > 0:
            critical_items.append({
                "item": "Structural modifications",
                "duration": "4–8 weeks",
                "note": "May require engineering review and permit updates"
            })
        
        if categories.get('MEP', 0) > 0 or categories.get('Electrical', 0) > 0:
            critical_items.append({
                "item": "MEP coordination",
                "duration": "3–6 weeks",
                "note": "Requires coordination between trades"
            })
        
        critical_items.append({
            "item": "Permitting",
            "duration": "2–4 weeks",
            "note": "Can run in parallel with design revisions"
        })
        
        return {
            "criticalPathItems": critical_items,
            "overlapSummary": f"With {total_changes} changes detected, sequential execution could take 2-4 months. Smart overlap of permitting and procurement can compress this to 1-2 months.",
            "scenarios": [
                {
                    "name": "Best-case (parallelized)",
                    "description": "All activities run in parallel where possible",
                    "impact": "+1 month",
                    "probability": 25,
                    "color": "green"
                },
                {
                    "name": "Typical-case",
                    "description": "Some delays in permitting or coordination",
                    "impact": "+2 months",
                    "probability": 50,
                    "color": "yellow"
                },
                {
                    "name": "Worst-case (serial)",
                    "description": "Sequential execution with delays",
                    "impact": "+3–4 months",
                    "probability": 25,
                    "color": "red"
                }
            ],
            "bottomLine": "Early coordination and parallel permitting are key to minimizing schedule impact. AI-generated detailed analysis unavailable."
        }


# Singleton instance
_impact_report_service = None

def get_impact_report_service() -> ImpactReportService:
    """Get singleton instance of ImpactReportService."""
    global _impact_report_service
    if _impact_report_service is None:
        _impact_report_service = ImpactReportService()
    return _impact_report_service

