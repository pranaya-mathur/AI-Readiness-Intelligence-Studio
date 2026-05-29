import json
import logging
import re
import requests
from typing import Dict, Any, List
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMRouter")


def _extract_prompt_field(prompt: str, label: str) -> str:
    pattern = rf"{re.escape(label)}:\s*(.+?)(?=\n[A-Z][A-Za-z /&_-]+:|\Z)"
    match = re.search(pattern, prompt, flags=re.DOTALL)
    if not match:
        return ""
    return " ".join(match.group(1).strip().split())


def _extract_list(prompt: str, label: str) -> List[str]:
    value = _extract_prompt_field(prompt, label)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _title_from_phrase(phrase: str) -> str:
    words = [word for word in re.split(r"[^A-Za-z0-9]+", phrase) if word]
    return " ".join(word.capitalize() for word in words[:4])


class LLMRouter:
    @staticmethod
    def generate_completion(
        prompt: str,
        system_prompt: str = "You are an expert AI transformation consultant and enterprise architect.",
        temperature: float = 0.2,
        max_tokens: int = 4000,
        require_json: bool = False,
    ) -> str:
        """
        Attempts to generate completion using:
        1. Groq (llama-3.3-70b-versatile)
        2. Ollama (qwen3.5:9b or llama3:8b)
        3. Local Mockup (dynamic heuristic fallback)
        """
        # Formulate payload
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # 1. Try Groq (if key available and USE_OLLAMA is false)
        if settings.GROQ_API_KEY and not settings.USE_OLLAMA:
            try:
                logger.info("Routing request to GROQ (llama-3.3-70b-versatile)...")
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload: dict[str, Any] = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if require_json:
                    payload["response_format"] = {"type": "json_object"}

                response = requests.post(url, headers=headers, json=payload, timeout=8)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    logger.warning(
                        f"GROQ failed with code {response.status_code}: {response.text}"
                    )
            except Exception as e:
                logger.warning(f"Error connecting to GROQ: {e}")

        # 2. Fall back to Ollama
        logger.info("Routing request to Local Ollama...")
        # Select best model based on require_json
        model = (
            settings.OLLAMA_STRUCTURED_MODEL
            if require_json
            else settings.OLLAMA_REASONING_MODEL
        )
        try:
            url = f"{settings.OLLAMA_HOST}/api/chat"
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "options": {"temperature": temperature},
                "stream": False,
            }
            if require_json:
                payload["format"] = "json"

            response = requests.post(url, json=payload, timeout=12)
            if response.status_code == 200:
                return response.json()["message"]["content"]
            else:
                logger.warning(
                    f"Ollama failed with code {response.status_code}: {response.text}"
                )
        except Exception as e:
            logger.warning(f"Error connecting to Ollama: {e}")

        # 3. Last resort: Mock response generator based on prompts
        logger.warning(
            "Both Groq and Ollama are unavailable. Routing to Local Deterministic Fallback Engine."
        )
        return LLMRouter._generate_fallback_response(prompt, require_json)

    @staticmethod
    def generate_embeddings(text: str) -> List[float]:
        """
        Attempts to generate embeddings using Ollama (nomic-embed-text:latest).
        Falls back to a deterministic hashing index of floats if Ollama is offline.
        """
        if not settings.USE_OLLAMA:
            # Fallback to local numpy vector space
            return LLMRouter._mock_embeddings(text)

        try:
            url = f"{settings.OLLAMA_HOST}/api/embeddings"
            payload = {"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": text}
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json()["embedding"]
        except Exception as e:
            logger.warning(
                f"Ollama embeddings failed ({e}). Generating static placeholder floats."
            )

        return LLMRouter._mock_embeddings(text)

    @staticmethod
    def _mock_embeddings(text: str) -> List[float]:
        """Generates a pseudo-random, deterministic embedding vector (size 384) based on text hash"""
        import hashlib
        import numpy as np

        # Calculate MD5 hash
        h = hashlib.md5(text.encode("utf-8")).hexdigest()
        # Seed generator with hash value
        seed = int(h[:8], 16)
        np.random.seed(seed)
        vec = np.random.randn(384)
        # Normalize
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()

    @staticmethod
    def _generate_fallback_response(prompt: str, require_json: bool) -> str:
        """Determining heuristic response to keep code executing in offline conditions"""
        company = _extract_prompt_field(
            prompt, "Company Name"
        ) or _extract_prompt_field(
            prompt, "Build a 30/60/90 day roadmap containing 3 strategic steps for"
        )
        _extract_prompt_field(prompt, "Industry")
        goals = _extract_prompt_field(prompt, "Goals") or _extract_prompt_field(
            prompt, "Main Goals"
        )
        pain_points = _extract_list(prompt, "Pain Points") or _extract_list(
            prompt, "Analyze these pain points"
        )
        departments = _extract_list(prompt, "Departments")
        current_tools = _extract_list(prompt, "Current Tools")
        compliance = _extract_list(prompt, "Compliance Requirements") or _extract_list(
            prompt, "For these compliance requirements"
        )

        if not departments:
            departments = ["Operations", "Customer Support"]
        if not pain_points:
            pain_points = ["Manual Process Overload", "Data Silos"]

        def bottleneck_from_pain(pain: str, idx: int) -> Dict[str, Any]:
            mapped_departments = departments or ["Operations"]
            department = mapped_departments[min(idx, len(mapped_departments) - 1)]
            lower_pain = pain.lower()
            if "proposal" in lower_pain or "sales" in lower_pain:
                return {
                    "department": "Sales & Pre-sales"
                    if "Sales & Pre-sales" in mapped_departments
                    else department,
                    "process_name": "Proposal Drafting and Response Assembly",
                    "bottleneck_description": f"{company or 'The team'} still assembles proposal narratives manually across reusable decks, pricing notes, and prior client responses.",
                    "ai_potential": "High",
                }
            if (
                "support" in lower_pain
                or "ticket" in lower_pain
                or "customer" in lower_pain
            ):
                return {
                    "department": "Customer Support"
                    if "Customer Support" in mapped_departments
                    else department,
                    "process_name": "Ticket Triage and Response Drafting",
                    "bottleneck_description": "Support analysts are manually classifying inbound requests and repeating the same first-response language across common cases.",
                    "ai_potential": "High",
                }
            if "compliance" in lower_pain or "audit" in lower_pain:
                return {
                    "department": "Compliance & Governance"
                    if "Compliance & Governance" in mapped_departments
                    else department,
                    "process_name": "Policy and Control Evidence Review",
                    "bottleneck_description": "Audit evidence and policy checks are still reviewed line by line, slowing turnaround for governance requests.",
                    "ai_potential": "Medium",
                }
            if "data" in lower_pain:
                return {
                    "department": department,
                    "process_name": "Cross-System Data Consolidation",
                    "bottleneck_description": f"Teams are reconciling information manually across {', '.join(current_tools[:2]) or 'multiple systems'}, which creates reporting lag and inconsistent handoffs.",
                    "ai_potential": "High",
                }
            return {
                "department": department,
                "process_name": f"{_title_from_phrase(pain)} Workflow",
                "bottleneck_description": f"{company or 'The client'} is still handling '{pain}' through manual coordination rather than a reusable AI-assisted workflow.",
                "ai_potential": "Medium",
            }

        def use_case_from_bottleneck(
            bottleneck: Dict[str, Any], idx: int
        ) -> Dict[str, Any]:
            department = bottleneck["department"]
            process_name = bottleneck["process_name"]
            tool_hint = (
                current_tools[idx]
                if idx < len(current_tools)
                else (current_tools[0] if current_tools else "existing systems")
            )
            if "Proposal" in process_name:
                return {
                    "use_case_name": "Intelligent Pre-Sales Proposal Copilot",
                    "department": department,
                    "description": "Intelligent solution drafting companion that pulls from verified proposal assets and past winning bid documents to build compliance-mapped proposal outlines.",
                    "value": "High",
                    "complexity": "Low",
                    "risk": "Low",
                    "priority": "P1",
                    "evidence": f"Recommended because '{process_name}' is manual today and the stated goal is '{goals or 'faster service delivery'}'.",
                    "confidence": 91.0,
                }
            if "Ticket" in process_name or "Response" in process_name:
                return {
                    "use_case_name": "Support Intake and Draft Response Assistant",
                    "department": department,
                    "description": "Classify inbound requests, draft suggested replies, and route cases to the right queue using grounded internal knowledge.",
                    "value": "High",
                    "complexity": "Medium",
                    "risk": "Medium",
                    "priority": "P1",
                    "evidence": f"Recommended because '{process_name}' repeats the same low-value work and relies on existing systems such as {tool_hint}.",
                    "confidence": 89.0,
                }
            if "Policy" in process_name or "Audit" in process_name:
                return {
                    "use_case_name": "Compliance Evidence Review Assistant",
                    "department": department,
                    "description": "Summarize policy obligations, highlight missing control evidence, and prepare review packets for human approval.",
                    "value": "High",
                    "complexity": "Medium",
                    "risk": "High",
                    "priority": "P2",
                    "evidence": f"Recommended because the intake includes {', '.join(compliance) or 'formal compliance requirements'} and manual governance review remains slow.",
                    "confidence": 86.0,
                }
            return {
                "use_case_name": f"{department} Workflow Intelligence Assistant",
                "department": department,
                "description": f"Guide teams through '{process_name}' with structured AI assistance, summarized evidence, and reusable task handoffs.",
                "value": "Medium",
                "complexity": "Low",
                "risk": "Low",
                "priority": "P2",
                "evidence": f"Recommended because '{process_name}' is still manual and tied to pain points like {pain_points[idx % len(pain_points)]}.",
                "confidence": 84.0,
            }

        derived_bottlenecks = [
            bottleneck_from_pain(pain, idx) for idx, pain in enumerate(pain_points[:3])
        ]
        derived_use_cases = [
            use_case_from_bottleneck(item, idx)
            for idx, item in enumerate(derived_bottlenecks[:3])
        ]
        goals_lower = goals.lower()
        if "proposal" in goals_lower:
            derived_use_cases.insert(
                0,
                {
                    "use_case_name": "Intelligent Pre-Sales Proposal Copilot",
                    "department": "Sales & Pre-sales"
                    if "Sales & Pre-sales" in departments
                    else departments[0],
                    "description": "Intelligent solution drafting companion that pulls from verified proposal assets and past winning bid documents to build compliance-mapped proposal outlines.",
                    "value": "High",
                    "complexity": "Low",
                    "risk": "Low",
                    "priority": "P1",
                    "evidence": f"Recommended because the stated business goal is '{goals}' and the delivery model still depends on manual proposal assembly.",
                    "confidence": 91.0,
                },
            )
        if "support" in goals_lower or "ticket" in goals_lower:
            derived_use_cases.insert(
                1 if derived_use_cases else 0,
                {
                    "use_case_name": "Support Intake and Draft Response Assistant",
                    "department": "Customer Support"
                    if "Customer Support" in departments
                    else departments[0],
                    "description": "Classify inbound requests, suggest grounded replies, and route cases to the right queue using internal knowledge.",
                    "value": "High",
                    "complexity": "Medium",
                    "risk": "Medium",
                    "priority": "P1",
                    "evidence": f"Recommended because the goal explicitly mentions support ticket parsing and current work still relies on {', '.join(current_tools[:2]) or 'manual systems'}.",
                    "confidence": 89.0,
                },
            )
        deduped_use_cases = []
        seen_use_case_names = set()
        for use_case in derived_use_cases:
            if use_case["use_case_name"] in seen_use_case_names:
                continue
            seen_use_case_names.add(use_case["use_case_name"])
            deduped_use_cases.append(use_case)
        derived_use_cases = deduped_use_cases[:3]

        # If JSON required, inspect the prompt keyword to send realistic consulting records
        if require_json:
            if "use_case" in prompt.lower() or "opportunity" in prompt.lower():
                return json.dumps({"use_cases": derived_use_cases})
            elif "bottleneck" in prompt.lower():
                return json.dumps({"bottlenecks": derived_bottlenecks[:2]})
            elif "risk" in prompt.lower():
                return json.dumps(
                    {
                        "risks": [
                            {
                                "risk_name": "Sensitive data exposure in AI-assisted workflows",
                                "severity": "High" if compliance else "Medium",
                                "recommendation": f"Enforce human approval, source logging, and redaction controls before AI outputs are shared across {', '.join(compliance) or 'client-facing workflows'}.",
                                "is_control_met": 0,
                            },
                            {
                                "risk_name": "Low-trust automation recommendations without grounded evidence",
                                "severity": "Medium",
                                "recommendation": f"Require reviewers to validate outputs that depend on {', '.join(current_tools[:2]) or 'multiple internal tools'} until evaluation baselines are stable.",
                                "is_control_met": 0,
                            },
                        ]
                    }
                )
            elif "roadmap" in prompt.lower():
                top_use_case = (
                    derived_use_cases[0]["use_case_name"]
                    if derived_use_cases
                    else "AI workflow assistant"
                )
                return json.dumps(
                    {
                        "roadmap": [
                            {
                                "phase": "30-Day",
                                "action_item": f"Finalize a scoped pilot around {top_use_case}, confirm success metrics, and assemble the highest-value documents and workflows for {company or 'the client'}.",
                                "expected_impact": "Creates a grounded pilot scope with measurable value and cleaner evidence inputs.",
                                "confidence": 90.0,
                            },
                            {
                                "phase": "60-Day",
                                "action_item": f"Run a controlled MVP with human review enabled across {', '.join(departments[:2]) or 'priority teams'} and connect it to the main operating tools.",
                                "expected_impact": "Reduces turnaround time on repetitive work while preserving trust and review checkpoints.",
                                "confidence": 85.0,
                            },
                            {
                                "phase": "90-Day",
                                "action_item": "Expand governance, adoption training, and executive reporting so the pilot can become a repeatable consulting offer.",
                                "expected_impact": "Turns a one-off pilot into a reusable operating model with stronger controls and internal buy-in.",
                                "confidence": 95.0,
                            },
                        ]
                    }
                )
            # Default empty JSON structure
            return "{}"
        else:
            primary_departments = ", ".join(departments[:3]) or "core operating teams"
            primary_pains = (
                ", ".join(pain_points[:2]).lower() or "manual coordination work"
            )
            tools_phrase = ", ".join(current_tools[:3]) or "existing internal systems"
            goals_phrase = goals or "improve delivery speed and reduce manual effort"
            return (
                f"{company or 'The organization'} appears best suited for a controlled AI pilot focused on {primary_departments}. "
                f"The current operating model still shows friction around {primary_pains}, while teams already rely on {tools_phrase} as workable source systems. "
                f"A phased rollout tied to the goal '{goals_phrase}' would create near-term value without overextending governance risk."
            )
