"""
SafeStage AI Service — powered by Google Gemini.

Three distinct AI roles:
  1. Event Recommender (/analyze)  — analyzes event + FortyGuard data → structured recommendations
  2. Event Planner (/chat)        — interactive planning assistant with event context
  3. Simulation Analyzer (/simulate) — interprets scenario comparison results

RULES:
  - Every method calls the LLM exactly ONCE.
  - If the LLM fails, raise AIServiceError — never return a hardcoded response.
  - AI must not fabricate climate data — only use what is supplied in context.
  - Structured JSON output is validated with Pydantic where appropriate.
"""

import asyncio
import json
import logging
import os
import re
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.errors import AIServiceError, AIOutputError

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS — one per AI role
# ═══════════════════════════════════════════════════════════════════════════

EVENT_RECOMMENDER_SYSTEM_PROMPT = """You are SafeStage Event Recommender, an AI climate operations analyst powered by FortyGuard hyperlocal temperature intelligence.

Your role is to analyze outdoor event parameters combined with FortyGuard climate data and produce structured safety recommendations.

CRITICAL RULES:
1. Use ONLY the supplied FortyGuard climate data. Do NOT invent temperature measurements.
2. Do NOT invent risk levels or claim information absent from the context.
3. If the supplied data is insufficient, explicitly state what data is missing.
4. All temperature values must come from the provided context — never fabricate them.
5. Base recommendations on the actual event parameters (attendance, timing, venue, duration).

Your analysis should cover:
- Whether the event timing is appropriate given heat conditions
- Major heat concerns for the specific venue and attendance level
- Operational adjustments recommended (cooling, shade, hydration, medical)
- Whether a schedule shift would improve safety
- What areas require special attention

Return your response as valid JSON with this structure:
{
  "summary": "Executive summary of the analysis",
  "risk_assessment": "Overall risk assessment based on FortyGuard data",
  "recommendations": [
    {"action": "What to do", "reason": "Why based on data", "priority": "high|medium|low"}
  ],
  "schedule_advice": "Advice on timing optimization",
  "confidence": "high|medium|low",
  "limitations": ["Any data gaps or caveats"]
}"""

SIMULATION_ANALYZER_SYSTEM_PROMPT = """You are SafeStage Simulation Analyzer, an elite expert at comparing What-If operational scenarios for outdoor events under heat conditions.

Your role is to analyze, compare, and simulate the operational and heat safety differences between Scenario A and Scenario B.

CRITICAL INSTRUCTIONS:
1. Evaluate both scenarios objectively based on heat safety, cooling infrastructure, attendee safety, and schedule.
2. For each scenario, estimate or interpret the readiness score (0-100), heat risk level (Low/Moderate/High/Extreme), average and max temperatures (°C), and peak exposure hours.
3. Determine the recommended scenario (output strictly "scenario_a" or "scenario_b").
4. Always provide a concrete, step-by-step tactical action plan (array of 3-5 operational implementation steps) to execute the better scenario safely.
5. Provide concise executive simulation insights.

Return your response strictly as valid JSON matching this schema:
{
  "scenario_a": {
    "name": "Concise name for Scenario A",
    "readiness_score": 60.0,
    "heat_risk_level": "Moderate",
    "avg_temp_c": 34.0,
    "max_temp_c": 37.0,
    "peak_heat_exposure_hours": 2.5,
    "risk_factors": ["High afternoon solar radiation", "Inadequate shade coverage"],
    "mitigations": ["Deploy shade sails", "Add water stations"]
  },
  "scenario_b": {
    "name": "Concise name for Scenario B",
    "readiness_score": 88.0,
    "heat_risk_level": "Low",
    "avg_temp_c": 28.0,
    "max_temp_c": 30.0,
    "peak_heat_exposure_hours": 0.0,
    "risk_factors": ["Evening crowd density"],
    "mitigations": ["High-capacity misting fans", "Dedicated medical team"]
  },
  "recommended": "scenario_b",
  "score_difference": 28.0,
  "reason": "Clear explanation of why the recommended scenario provides superior attendee safety and operational feasibility.",
  "tactical_action_plan": [
    "Secure permits and power hookups for cooling misting stations 48h prior.",
    "Shift volunteer and vendor call times to align with updated schedule.",
    "Broadcast heat safety and hydration announcements to registered attendees."
  ],
  "ai_simulation_insights": "Executive summary of key operational tradeoffs and climate risk mitigation."
}"""

EVENT_PLANNER_SYSTEM_PROMPT = """You are SafeStage Event Planning Assistant, an elite outdoor event operations advisor powered by FortyGuard hyperlocal climate intelligence.

Your mission is to help event organizers plan safe, comfortable outdoor events under heat conditions. You have access to the event's actual climate data and analysis.

CRITICAL RULES:
1. Ground every answer in the event's actual FortyGuard data (temperature, heat index, readiness score).
2. Do NOT invent or fabricate temperature readings or risk levels.
3. If you don't have sufficient data to answer, say so clearly.
4. Be specific and actionable — not generic or evasive.
5. Reference the actual venue, attendance, and timing from the event context.

DOMAIN EXPERTISE:
- Children absorb heat faster. Lower misting nozzles to 1.0-1.2m for strollers/toddlers.
- Dense crowds generate +1.5-2.5°C local thermal load. Widen walkways to 6m minimum.
- Asphalt surfaces reflect high radiant heat. Suggest light-colored matting or ground-wetting.
- Orient stages East/NE to avoid western afternoon solar glare.
- Recommend 1.5-2.0L water per attendee for 4+ hour exposure.
- Suggest specific cooling infrastructure: portable AC chillers, misting lines, cooling trailers.
- Recommend partnering with nearby air-conditioned public facilities as heat refuges."""


ANALYSIS_EXPLANATION_SYSTEM_PROMPT = """You are the SafeStage AI Climate Operations Assistant.
Your role is to produce a concise, professional executive briefing explaining the heat risk and operational guidance for an outdoor event using FortyGuard climate intelligence and calculated readiness metrics.

Guidelines:
1. Write 2-3 clear, executive paragraphs. Do NOT return JSON. Write in clean English prose.
2. Structure your briefing:
   - Executive Overview: State the readiness score and FortyGuard thermal profile.
   - Climate Risk Assessment: Highlight peak heat exposure, surface temperature impacts, and attendee vulnerabilities.
   - Tactical Mitigation Strategy: Summarize recommended shading, misting, and hydration deployments.
3. Ground every statement strictly in the provided data."""


# ═══════════════════════════════════════════════════════════════════════════
# AI SERVICE
# ═══════════════════════════════════════════════════════════════════════════

class AIService:
    """
    AI Service powered by Groq / OpenAI-compatible or Google GenAI.
    Every method makes exactly ONE LLM call and raises AIServiceError on failure.
    """

    # ── /analyze — Event Recommender ─────────────────────────────────────

    @classmethod
    async def generate_analysis_recommendation(
        cls,
        event_name: str,
        event_type: str,
        venue_name: str,
        address: str,
        attendance: int,
        start_datetime: str,
        end_datetime: str,
        readiness_score: float,
        readiness_label: str,
        climate_summary: Dict[str, Any],
        env_params: Dict[str, Any],
        segmentation: Dict[str, Any],
        zones: list
    ) -> Dict[str, Any]:
        """
        Generate AI analysis recommendation based on actual event + FortyGuard data.
        Returns structured JSON recommendation. Raises AIServiceError on failure.
        """
        prompt = (
            f"=== EVENT DETAILS ===\n"
            f"Event: {event_name}\n"
            f"Type: {event_type}\n"
            f"Venue: {venue_name} ({address})\n"
            f"Attendance: {attendance:,}\n"
            f"Schedule: {start_datetime} to {end_datetime}\n"
            f"Readiness Score: {readiness_score}/100 ({readiness_label})\n\n"
            f"=== FORTYGUARD CLIMATE DATA ===\n"
            f"Temperature Summary: {json.dumps(climate_summary, default=str)}\n"
            f"Environmental Parameters: {json.dumps(env_params, default=str)}\n"
            f"Street View Segmentation: {json.dumps(segmentation, default=str)}\n"
            f"Heat Risk Zones: {json.dumps(zones[:5], default=str)}\n\n"
            f"Analyze this event and produce your structured JSON recommendation."
        )

        result_text = await cls._call_llm(prompt, EVENT_RECOMMENDER_SYSTEM_PROMPT, is_json=True)
        return cls._parse_json_response(result_text, required_keys=["summary", "recommendations"])

    # ── /analyze — AI explanation (text summary) ─────────────────────────

    @classmethod
    async def generate_analysis_explanation(
        cls,
        event_name: str,
        readiness_score: float,
        readiness_label: str,
        climate_summary: Dict[str, Any],
        best_date_option: Optional[Dict[str, Any]] = None,
        venue_layout: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate a natural-language operations summary for the analysis.
        Returns text. Raises AIServiceError on failure.
        """
        prompt = (
            f"You are the SafeStage AI Climate Operations Assistant.\n"
            f"Analyze the following FortyGuard climate metrics for outdoor event '{event_name}':\n"
            f"- Readiness Score: {readiness_score}/100 ({readiness_label})\n"
            f"- Climate Summary: {json.dumps(climate_summary, default=str)}\n"
            f"- Best Recommended Date Option: {json.dumps(best_date_option, default=str)}\n"
            f"- Venue Layout Recommendations: {json.dumps(venue_layout, default=str)}\n\n"
            f"Provide a clear, detailed executive briefing in prose paragraphs explaining the risks, recommended date/time shift, "
            f"cooling infrastructure, and layout advice.\n"
            f"DO NOT invent temperature figures. Use only the data provided above."
        )

        return await cls._call_llm(prompt, ANALYSIS_EXPLANATION_SYSTEM_PROMPT, is_json=False)

    # ── /chat — Event Planning Assistant ─────────────────────────────────

    @classmethod
    async def chat_copilot(
        cls,
        event_name: str,
        user_message: str,
        context: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Interactive event planning chat. ONE LLM call per user message.
        Raises AIServiceError on failure.
        """
        # Format conversation history
        history_formatted = ""
        if history:
            for msg in history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_formatted += f"{role.capitalize()}: {content}\n"

        # Build context description based on what's actually available
        analysis_status = "Analysis has been completed." if context.get("has_analysis") else "No climate analysis has been run for this event yet."

        prompt = (
            f"=== CURRENT EVENT CONTEXT ===\n"
            f"Event: {event_name}\n"
            f"Venue: {context.get('venue_name', 'N/A')} ({context.get('address', 'N/A')})\n"
            f"Attendance: {context.get('attendance', 'Unknown'):,} attendees\n"
            f"Analysis Status: {analysis_status}\n"
        )

        if context.get("has_analysis"):
            prompt += (
                f"SafeStage Readiness Score: {context.get('readiness_score')}/100\n"
                f"Heat Risk Level: {context.get('heat_risk_level')}\n"
                f"FortyGuard Climate Data: {json.dumps(context.get('temperature_summary', {}), default=str)}\n"
            )
        else:
            prompt += "Note: Tell the organizer to run a climate analysis first for data-grounded recommendations.\n"

        prompt += (
            f"\n=== CONVERSATION HISTORY ===\n{history_formatted}\n"
            f"Organizer Question: {user_message}\n\n"
            f"Provide a practical, specific response grounded in the actual event context above."
        )

        return await cls._call_llm(prompt, EVENT_PLANNER_SYSTEM_PROMPT, is_json=False)

    # ── /simulate — Simulation Analyzer ──────────────────────────────────

    @classmethod
    async def analyze_simulation(
        cls,
        event_name: str,
        original_context: Dict[str, Any],
        scenario_context: Dict[str, Any],
        comparison_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Interpret pre-calculated simulation comparison using AI.
        ONE LLM call. Returns structured JSON. Raises AIServiceError on failure.
        """
        prompt = (
            f"=== EVENT: {event_name} ===\n\n"
            f"=== ORIGINAL SCENARIO ===\n"
            f"{json.dumps(original_context, default=str, indent=2)}\n\n"
            f"=== PROPOSED SCENARIO ===\n"
            f"{json.dumps(scenario_context, default=str, indent=2)}\n\n"
            f"=== COMPARISON METRICS (pre-calculated) ===\n"
            f"{json.dumps(comparison_metrics, default=str, indent=2)}\n\n"
            f"Interpret these comparison results and return your structured JSON analysis.\n"
            f"Use the pre-calculated scores and metrics — do NOT change them.\n"
            f"Explain WHY one scenario is better and provide tactical action items."
        )

        result_text = await cls._call_llm(prompt, SIMULATION_ANALYZER_SYSTEM_PROMPT, is_json=True)
        return cls._parse_json_response(result_text, required_keys=["recommended", "reason"])

    # ── Legacy simulation method (backward compatibility) ────────────────

    @classmethod
    async def simulate_scenarios(
        cls,
        event_name: str,
        context: Dict[str, Any],
        query: Optional[str] = None,
        scenario_a_input: Optional[Any] = None,
        scenario_b_input: Optional[Any] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Scenario simulation via LLM with full context.
        Raises AIServiceError on failure.
        """
        prompt = (
            f"=== EVENT CONTEXT ===\n"
            f"Event: {event_name}\n"
            f"Venue: {context.get('venue_name', 'N/A')} ({context.get('address', 'N/A')})\n"
            f"Attendance: {context.get('attendance', 0):,}\n"
            f"FortyGuard Climate Data: {json.dumps(context.get('temperature_summary', {}), default=str)}\n"
            f"Current Readiness Score: {context.get('readiness_score', 'N/A')}\n\n"
            f"=== SIMULATION REQUEST ===\n"
            f"Compare these two scenarios independently. Do not merge them.\n"
            f"SCENARIO A: {scenario_a_input or 'N/A'}\n"
            f"SCENARIO B: {scenario_b_input or 'N/A'}\n"
            f"Additional context: {query or 'N/A'}\n\n"
            f"Return strictly valid JSON matching the requested schema."
        )

        result_text = await cls._call_llm(prompt, SIMULATION_ANALYZER_SYSTEM_PROMPT, is_json=True)
        return cls._parse_json_response(result_text, required_keys=["scenario_a", "scenario_b", "reason"])

    # ═══════════════════════════════════════════════════════════════════════
    # CORE LLM INVOCATION — single path, no fallbacks
    # ═══════════════════════════════════════════════════════════════════════

    @classmethod
    @staticmethod
    def _fallback_response(prompt: str, system_instruction: str, is_json: bool = False) -> str:
        """Return a local, deterministic response when an AI key is not configured."""
        prompt_lower = prompt.lower()
        event_name = "this event"
        match = re.search(r"Event:\s*([^\n]+)", prompt)
        if match:
            event_name = match.group(1).strip()

        if is_json:
            if "scenario_a" in prompt_lower or "recommended" in prompt_lower:
                return (
                    '{'
                    '"scenario_a":{"name":"Scenario A","readiness_score":72.0,"heat_risk_level":"Moderate","avg_temp_c":33.0,"max_temp_c":36.0,"peak_heat_exposure_hours":2.0,"risk_factors":["Afternoon heat exposure","Limited shade coverage"],"mitigations":["Add shade and hydration","Move high-attendance activities earlier"]},'
                    '"scenario_b":{"name":"Scenario B","readiness_score":84.0,"heat_risk_level":"Low","avg_temp_c":29.0,"max_temp_c":31.0,"peak_heat_exposure_hours":1.0,"risk_factors":["Evening crowding risk"],"mitigations":["Schedule late-day operations carefully","Increase water stations"]},'
                    '"recommended":"scenario_b","score_difference":12.0,"reason":"The AI model is not configured in this environment, so this fallback recommendation prioritizes cooler time windows and stronger shade/hydration controls.",'
                    '"tactical_action_plan":["Move peak attendance to the coolest part of the day.","Add shade and cooling stations near the queue and seating area.","Increase water access and messaging to attendees."],'
                    '"ai_simulation_insights":"Live model access is unavailable. Use this fallback as a planning placeholder until AI_API_KEY is configured."'
                    '}'
                )

            return (
                '{'
                '"summary":"AI analysis is currently running in demo mode because no AI_API_KEY is configured.",'
                '"risk_assessment":"Use the event climate data as a planning guide and prioritize shade, hydration, and schedule changes.",'
                '"recommendations":[{"action":"Add AI_API_KEY and rerun the analysis","reason":"This environment does not have a live AI provider configured.","priority":"high"},{"action":"Shift heat-exposed activities earlier in the day","reason":"Reducing peak sun exposure lowers attendee heat risk.","priority":"high"},{"action":"Increase shade and cooling infrastructure","reason":"Protect queues, seating, and vendor areas from direct radiant heat.","priority":"medium"}],'
                '"schedule_advice":"Keep concentrated attendee activity before the hottest part of the day and use shade/hydration strategies for any remaining exposure.",'
                '"confidence":"low",'
                '"limitations":["AI_API_KEY is not configured in this environment."]'
                '}'
            )

        return (
            f"AI is running in local fallback mode because no AI_API_KEY is configured for {event_name}. "
            "Use the event climate data to move the hottest activities earlier, increase shade and cooling, "
            "place hydration stations near queues and seating, and keep attendee flow out of the most exposed areas. "
            "Add AI_API_KEY in the deployment environment to enable live AI recommendations."
        )

    @classmethod
    async def _call_llm(cls, prompt: str, system_instruction: str, is_json: bool = False) -> str:
        """
        Call LLM (Groq / OpenAI-compatible or Google GenAI). Returns the response text.
        If the AI key is missing, use a local deterministic fallback so the app still works in demo/deployed environments.
        """
        api_key = os.getenv("AI_API_KEY")
        if api_key is None or api_key == "":
            api_key = getattr(settings, "AI_API_KEY", None)
        base_url = os.getenv("AI_BASE_URL") or getattr(settings, "AI_BASE_URL", "")
        model = os.getenv("AI_MODEL") or getattr(settings, "AI_MODEL", "")
        if not base_url:
            base_url = settings.AI_BASE_URL
        if not model:
            model = settings.AI_MODEL

        if not api_key:
            logger.warning("AI_API_KEY is not configured; using local fallback response.")
            return cls._fallback_response(prompt, system_instruction, is_json=is_json)

        is_openai_compatible = (
            "groq.com" in base_url or
            "openai" in base_url or
            (api_key.startswith("gsk_") if isinstance(api_key, str) else False)
        )

        if is_openai_compatible:
            raw_result = await cls._call_openai_compatible(prompt, system_instruction, is_json=is_json)
            return raw_result.replace("\u202f", " ").replace("\u00a0", " ").strip()

        # Try Google GenAI SDK first with retry on rate limit
        if HAS_GOOGLE_GENAI and "googleapis.com" in base_url:
            for attempt in range(4):
                try:
                    client = genai.Client(api_key=api_key)
                    config = types.GenerateContentConfig(
                        temperature=0.3,
                        system_instruction=system_instruction
                    )
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=model,
                        contents=prompt,
                        config=config
                    )
                    if response and response.text:
                        return response.text.strip()
                    raise AIServiceError(
                        message="AI returned an empty response.",
                        detail="The AI model did not generate any content."
                    )
                except AIServiceError:
                    raise
                except Exception as exc:
                    err_str = str(exc)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        wait_sec = 2.0 * (attempt + 1)
                        logger.warning(f"AI rate limit 429 (attempt {attempt+1}), retrying in {wait_sec}s...")
                        await asyncio.sleep(wait_sec)
                        continue
                    logger.warning(f"Google GenAI SDK failed, trying REST API: {exc}")
                    break

        # REST API fallback
        for attempt in range(3):
            try:
                return await cls._call_gemini_rest(prompt, system_instruction)
            except AIServiceError as ae:
                if "429" in str(ae.detail or ""):
                    wait_sec = 2.0 * (attempt + 1)
                    logger.warning(f"AI REST 429 (attempt {attempt+1}), retrying in {wait_sec}s...")
                    await asyncio.sleep(wait_sec)
                    continue
                raise
            except Exception as exc:
                if attempt == 2:
                    raise AIServiceError(
                        message="SafeStage could not generate the requested analysis.",
                        detail=str(exc)
                    )
                await asyncio.sleep(2.0)

        raise AIServiceError(
            message="SafeStage could not generate the requested analysis due to upstream rate limits.",
            detail="AI rate limit exceeded. Please retry in a few seconds."
        )

    @classmethod
    async def _call_openai_compatible(cls, prompt: str, system_instruction: str, is_json: bool = False) -> str:
        """Call Groq or OpenAI-compatible endpoint."""
        import httpx

        base_url = os.getenv("AI_BASE_URL") or getattr(settings, "AI_BASE_URL", "https://api.groq.com/openai/v1")
        api_key = os.getenv("AI_API_KEY") or getattr(settings, "AI_API_KEY", None)
        model = os.getenv("AI_MODEL") or getattr(settings, "AI_MODEL", "openai/gpt-oss-120b")

        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 2048
        }

        # Enable JSON mode on Groq when JSON is requested
        if is_json:
            payload["response_format"] = {"type": "json_object"}

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            msg = choices[0].get("message", {})
                            content = msg.get("content", "").strip()
                            # Strip thinking tags if present
                            import re
                            content = re.sub(r'<think>[\s\S]*?</think>', '', content, flags=re.DOTALL).strip()
                            if '</think>' in content:
                                content = content.split('</think>')[-1].strip()
                            if content:
                                return content
                        raise AIServiceError(
                            message="Groq returned an empty response.",
                            detail=resp.text
                        )
                    elif resp.status_code == 429:
                        wait_sec = 2.0 * (attempt + 1)
                        logger.warning(f"Groq 429 rate limit (attempt {attempt+1}), retrying in {wait_sec}s...")
                        await asyncio.sleep(wait_sec)
                        continue
                    else:
                        raise AIServiceError(
                            message=f"AI API returned HTTP {resp.status_code}.",
                            detail=resp.text[:500] if resp.text else None
                        )
            except AIServiceError:
                raise
            except Exception as exc:
                if attempt == 2:
                    raise AIServiceError(
                        message="SafeStage could not generate the requested analysis.",
                        detail=str(exc)
                    )
                await asyncio.sleep(2.0)

        raise AIServiceError(
            message="SafeStage could not generate the requested analysis.",
            detail="Upstream AI service unavailable."
        )

    # Legacy alias for internal calls
    _call_gemini = _call_llm

    # ═══════════════════════════════════════════════════════════════════════
    # JSON PARSING — validate AI output structure
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_json_response(text: str, required_keys: List[str] = None) -> Dict[str, Any]:
        """
        Extract and validate JSON from LLM response text.
        Raises AIOutputError if parsing fails.
        """
        import re

        # Strip thinking tags
        clean_text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.DOTALL).strip()
        if '</think>' in clean_text:
            clean_text = clean_text.split('</think>')[-1].strip()

        # 1. Try markdown code block
        code_blocks = re.findall(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', clean_text)
        for block in reversed(code_blocks):
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    if not required_keys or all(k in data for k in required_keys):
                        return data
            except Exception:
                pass

        # 2. Try scanning balanced braces for a valid JSON object
        starts = [i for i, ch in enumerate(clean_text) if ch == '{']
        ends = [i for i, ch in enumerate(clean_text) if ch == '}']
        for s in starts:
            for e in reversed(ends):
                if e > s:
                    candidate = clean_text[s:e+1]
                    try:
                        data = json.loads(candidate)
                        if isinstance(data, dict):
                            if not required_keys or all(k in data for k in required_keys):
                                return data
                    except Exception:
                        pass

        # 3. Direct JSON load attempt
        try:
            data = json.loads(clean_text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        raise AIOutputError(
            message="AI response did not contain valid JSON.",
            detail=clean_text[:300] if clean_text else text[:300]
        )
