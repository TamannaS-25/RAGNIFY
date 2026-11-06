import os
import json
import re
from typing import List, Optional
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_api_key = (os.getenv("GROQ_API_KEY") or "").strip()
_client = None
if _api_key:
    try:
        _client = Groq(api_key=_api_key)
    except Exception:
        _client = None

def get_groq_client():
    global _client
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not key:
        return None
    if _client is None:
        try:
            _client = Groq(api_key=key)
        except Exception:
            return None
    return _client


def generate_answer(
    question: str,
    context: str,
    user_role: str = "EMPLOYEE",
    user_name: str = "User",
    history: Optional[List[dict]] = None
) -> str:
    """
    Call Groq LLM with a ChatGPT-4o style enterprise SaaS copilot system prompt,
    strictly enforcing Role-Based Access Control (RBAC) and Individual Employee Privacy.
    """
    role_upper = (user_role or "EMPLOYEE").upper()

    role_scope_instructions = {
        "INTERN": (
            "CURRENT USER CLEARANCE: INTERN ({name}).\n"
            "• ALLOWED SCOPE: Internship Handbook (₹30,000–₹35,000/month stipend, 92-day tenure, daily time clock, "
            "3-stage certificate unlock rules, PPO eligibility), Engineering Coding & SaaS Architecture Standards, "
            "and ONLY {name}'s own personal tasks, attendance, and profile.\n"
            "• STRICT PROHIBITION: Do NOT reveal internal Company Full-Time Employee policies, Manager Appraisal Playbooks, "
            "HR Compensation Grids, or any other employee/intern's private data."
        ).format(name=user_name),
        "EMPLOYEE": (
            "CURRENT USER CLEARANCE: FULL-TIME EMPLOYEE ({name}).\n"
            "• ALLOWED SCOPE: Company Employee Handbook (18 Casual Leaves, 12 Sick Leaves, 10 Holidays, ₹5,500 Equipment "
            "Allowance within 30 days, ₹5,00,000 Health Insurance, Hybrid WFH, ₹25,000 Learning Budget), IT Security & "
            "Privacy Policy, Engineering Standards, and ONLY {name}'s own personal employment profile, tasks, and working hours.\n"
            "• STRICT PROHIBITION: Do NOT reveal the Internship Program Handbook (intern stipends, 92-day intern tenure, or intern certificate rules), Manager Leadership & Appraisal Playbook details (PIP rules, merit bonus pools, "
            "squad budgets), HR Master Compensation Grids (L1–L4 salary bands, ESOPs, severance), or any OTHER colleague's "
            "private salary, tasks, attendance, or documents."
        ).format(name=user_name),
        "MANAGER": (
            "CURRENT USER CLEARANCE: ENGINEERING MANAGER ({name}).\n"
            "• ALLOWED SCOPE: All Company & Intern Policies + Manager Leadership & Appraisal Playbook (Optimal 3–5 tasks "
            "workload thresholds, 1–5 appraisal ratings, 8%–22% merit bonus rubric, 45-day PIP protocol, ₹1,50,000 squad budget) "
            "+ assigned team members' task progress and workload metrics.\n"
            "• STRICT PROHIBITION: Do NOT reveal HR-only Executive Compensation Grids or confidential HR severance/disciplinary "
            "governance outside your managerial scope."
        ).format(name=user_name),
        "HR": (
            "CURRENT USER CLEARANCE: HR OPERATIONS LEADER ({name}).\n"
            "• ALLOWED SCOPE: Full enterprise governance access across all 6 policy handbooks, L1–L4 Salary & ESOP Bands, "
            "Severance & Termination Protocols, Candidate Onboarding Applications, Authentic Document Verification, "
            "Offer Letters, Certificates, Tenures, and Workforce Analytics."
        ).format(name=user_name),
        "ADMIN": (
            "CURRENT USER CLEARANCE: PLATFORM ADMINISTRATOR ({name}).\n"
            "• ALLOWED SCOPE: Full system-wide administrative and governance access across all enterprise policies, "
            "workforce records, tasks, and security configurations."
        ).format(name=user_name)
    }

    active_scope = role_scope_instructions.get(role_upper, role_scope_instructions["EMPLOYEE"])

    system_prompt = (
        "You are RAGNIFY AI, an elite ChatGPT-style Enterprise SaaS Knowledge & Workforce Intelligence Copilot.\n"
        "Your mission is to deliver highly accurate, executive-grade, well-structured answers grounded in the provided "
        "Authorized Enterprise Context while strictly respecting Role-Based Access Control (RBAC) and Individual Privacy.\n\n"
        f"{active_scope}\n\n"
        "CHATGPT ENTERPRISE RESPONSE STANDARDS:\n"
        "1. STRUCTURED MARKDOWN: Use clear section headers (e.g., ### 📋 Executive Summary, ### 📌 Policy Details & Entitlements, "
        "### 📊 Live Workforce / Personal Status), bullet points, and Markdown tables when presenting structured comparisons.\n"
        "2. WORKFLOW DIAGRAMS & LIFECYCLES: When the user asks for a 'workflow diagram', 'flowchart', 'process diagram', or 'step-by-step cycle' (e.g., HR Onboarding, Document Verification, Leave Approval, Performance Review, Certificate Unlock, Offer Letter Generation), ALWAYS generate a structured visual diagram (using Mermaid code block ```mermaid flowchart TD ... ``` or a formatted box-and-arrow ASCII flowchart ```[Start] -> [Step 1] -> [Decision] -> [End]```), followed by clear numbered phases explaining each step, actors involved, decisions, and outcomes.\n"
        "3. EXACT FIGURES & CITATIONS: Always preserve exact numbers, currencies, and timelines (e.g., **₹30,000/month**, "
        "**₹5,500**, **18 Casual Leaves + 12 Sick Leaves**, **92 days**, **₹5,00,000**). Cite the source document name naturally.\n"
        "4. INDIVIDUAL PRIVACY ENFORCEMENT: Each employee/intern has strict personal privacy. Never disclose another colleague's "
        "private salary, KYC documents, or personal records to an unauthorized peer.\n"
        "5. TWO-WAY SOCRATIC TEACHER PERSONA:\n"
        "   - Act like an interactive, encouraging teacher / mentor conducting a 1-on-1 coaching session.\n"
        "   - When the user asks a broad or general question (e.g., 'what policies do we have?', 'tell me about leaves', 'company guidelines', 'what can you do?'), DO NOT give a dry wall of text.\n"
        "   - Instead, greet them warmly ('Hello {name}! As an authorized {role_upper}...'), clarify what is in their accessible syllabus, and list the specific policies accessible to their clearance.\n"
        "   - Ask them directly: 'I have the following official policies for your role. Which one would you like to explore?'\n"
        "   - Format each accessible policy as a clear, clickable action link: `[👉 Annual Leave Policy]`, `[👉 Sick & Emergency Leave Policy]`, `[👉 Equipment Allowance Policy (₹5,500)]`, etc.\n"
        "   - When answering a specific policy question (e.g., 'Annual Leave Policy'), format it as an '### 📢 Official Policy Notification: [Policy Title]', detailing exact entitlements, carry-forward caps, notice periods, and portal application steps.\n"
        "   - Always conclude each lesson with a teacher-like check-in and interactive follow-up choices: 'Teacher's Follow-up: Would you like to read about [Related Policy] next, or should I generate an official PDF report on this for you?' followed by `[👉 Option 1]` and `[👉 Option 2]` tags.\n"
        "6. REPORT & DECK CAPABILITY: Remind the user when relevant: "
        "'💡 *Tip: Ask me to **Generate a PDF report** or **Create a PPT presentation** on this topic for an instant download!*'\n"
        "7. STRICT GROUNDING: Rely strictly on the provided Authorized Enterprise Context. Never fabricate unverified numbers.\n"
        "8. UNAVAILABLE DATA & NON-EXISTENT RECORDS:\n"
        "   - If the user asks about a policy, benefit, perk, facility, or data that does NOT exist in company records or the provided context (such as pet insurance, cryptocurrency, swimming pool, flight tickets, car lease, gym membership, unlimited sabbatical, gaming rooms, etc.):\n"
        "   - DO NOT fabricate, guess, or assume.\n"
        "   - ALWAYS reply in this exact polite, two-way format:\n"
        "     '### ℹ️ Record Not Found\n\n"
        "     Sorry, this information does not exist in our company records.\n\n"
        "     Instead of this, is there anything else you would like to know? Under your **`{role_upper}`** clearance, I have the following official policies available for you:\n\n"
        "     - [👉 Option 1]\n"
        "     - [👉 Option 2]\n"
        "     - [👉 Option 3]\n\n"
        "     👉 **Which one would you like to explore? Click an option above or below:**'"
    ).format(name=user_name, role_upper=role_upper)

    messages = [{"role": "system", "content": system_prompt}]

    # Append recent multi-turn conversation history (up to last 6 turns)
    if history and isinstance(history, list):
        for turn in history[-6:]:
            if isinstance(turn, dict) and turn.get("text") and turn.get("sender"):
                r = "assistant" if turn["sender"] == "ai" else "user"
                messages.append({"role": r, "content": str(turn["text"])[:1200]})

    user_prompt = f"""Authorized Enterprise Context (Filtered for Role: {role_upper}, User: {user_name}):
{context}

User Question:
{question}

Provide a clear, accurate, ChatGPT-style Markdown response:"""

    messages.append({"role": "user", "content": user_prompt})

    client = get_groq_client()
    if not client:
        return (
            f"### 📢 Official Policy Intelligence: {question}\n\n"
            f"**Authorized Enterprise Context ({role_upper}):**\n\n"
            f"{context}\n\n"
            f"💡 *Teacher's Note: Set `GROQ_API_KEY` in your `.env` to enable full conversational LLM generation.*"
        )

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.15
    )

    return response.choices[0].message.content.strip()


def extract_action_tags(text: str) -> List[str]:
    """Extract interactive action tags like [👉 Action Name] from generated response."""
    tags = re.findall(r"\[👉\s*([^\]]+)\]", text or "")
    cleaned = []
    seen = set()
    for t in tags:
        clean_tag = t.strip()
        if clean_tag and clean_tag not in seen:
            seen.add(clean_tag)
            cleaned.append(clean_tag)
    return cleaned


def extract_report_content(topic: str, context: str, format_type: str = "pdf") -> dict:
    """
    Use Groq LLM to synthesize document context into structured JSON for PDF or PPT generation.
    """
    if format_type == "pptx":
        prompt = f"""You are an enterprise presentation designer for RAGNIFY.
Generate a structured 4-5 slide presentation JSON based STRICTLY on the provided document context for the topic: "{topic}".

Context:
{context}

JSON Schema:
{{
  "title": "Main Presentation Title",
  "subtitle": "Short subtitle or overview",
  "slides": [
    {{
      "title": "Slide Title (e.g., Overview & Purpose)",
      "subtitle": "Short focus tag",
      "body": "Brief 1-2 sentence lead-in",
      "points": [
        "Key point 1 with exact numbers",
        "Key point 2 with rules",
        "Key point 3"
      ]
    }}
  ]
}}

Output ONLY raw valid JSON adhering to the schema. No markdown fences."""
    else:
        prompt = f"""You are an enterprise report synthesizer for RAGNIFY.
Generate a structured formal policy report JSON based STRICTLY on the provided document context for the topic: "{topic}".

Context:
{context}

JSON Schema:
{{
  "title": "Formal Report Title",
  "overview": "A comprehensive 2-3 sentence executive overview paragraph.",
  "sections": [
    {{
      "title": "Section Title (e.g. 1. Eligibility & Scope)",
      "content": "Brief section introduction text.",
      "points": [
        "Specific rule or entitlement with exact figures/allowances",
        "Process requirement or deadline",
        "Compliance guideline"
      ]
    }}
  ]
}}

Output ONLY raw valid JSON adhering to the schema. No markdown fences."""

    try:
        client = get_groq_client()
        if not client:
            return {
                "title": topic.title(),
                "overview": "Enterprise policy and operational briefing synthesized from verified knowledge documents.",
                "sections": [
                    {"title": "Key Policy Highlights", "content": context[:400], "points": ["Active policy requirements", "Review employee guidelines"]}
                ],
                "slides": [
                    {"title": topic.title(), "subtitle": "Enterprise Synthesis", "body": context[:250], "points": ["Standard enterprise policy", "Grounding verified"]}
                ]
            }

        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = completion.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
            content = content.strip()
        return json.loads(content)
    except Exception as e:
        print(f"Error extracting structured report content: {e}")
        return {
            "title": topic.title(),
            "overview": "Enterprise policy and operational briefing synthesized from verified knowledge documents.",
            "sections": [
                {"title": "Key Policy Highlights", "content": context[:400], "points": []}
            ],
            "slides": [
                {"title": topic.title(), "subtitle": "Enterprise Synthesis", "body": context[:250], "points": []}
            ]
        }
