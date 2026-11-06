import re
from typing import List, Optional
from rag.vector_store import search_documents_with_metadata, get_indexed_documents_summary
from rag.groq_service import generate_answer, extract_report_content, extract_action_tags
from services.report_generator_service import generate_pdf_report, generate_pptx_presentation


def detect_generation_intent(message: str) -> tuple[str, str]:
    """
    Detect if user is asking for a PDF report, PPT presentation, or regular chat.
    Returns: (format_type, topic) where format_type in ["pdf", "pptx", "none"]
    """
    msg_lower = message.lower()

    if any(k in msg_lower for k in ["ppt", "powerpoint", "presentation", "slides", "slide deck"]):
        topic = re.sub(
            r"(generate|create|make|give|download|export|prepare|a|an|the|ppt|powerpoint|presentation|slides|slide deck|for|on|about)",
            "",
            msg_lower,
            flags=re.IGNORECASE
        ).strip()
        topic = topic or "Enterprise Policy Overview"
        return "pptx", topic

    if any(k in msg_lower for k in [
        "pdf", "generate report", "download report", "export report",
        "create report", "policy report", "document report", "summary report"
    ]):
        topic = re.sub(
            r"(generate|create|make|give|download|export|prepare|a|an|the|pdf|report|document|summary report|policy report|for|on|about)",
            "",
            msg_lower,
            flags=re.IGNORECASE
        ).strip()
        topic = topic or "Enterprise Policy Report"
        return "pdf", topic

    return "none", ""


def _get_all_known_personnel_names() -> list[str]:
    """Return known workforce names from PostgreSQL and enterprise roster for Individual Privacy checks."""
    names = {
        "rahul verma", "rahul sharma", "vikram singh", "sneha reddy", "rohan gupta",
        "ananya roy", "karan malhotra", "neha sharma", "pooja nair", "aditya joshi",
        "meera iyer", "devansh jain", "sanjay kumar", "priya sharma", "vikram mehta",
        "priya nair", "aarav patel", "divya krishnan", "siddharth joshi", "kavita menon",
        "arjun nair", "nisha kapoor", "amit sharma", "karthik reddy"
    }
    try:
        from database import SessionLocal
        import models
        db = SessionLocal()
        try:
            for e in db.query(models.Employee).all():
                if e.name:
                    names.add(e.name.strip().lower())
            for c in db.query(models.CandidateProfile).all():
                if c.full_name:
                    names.add(c.full_name.strip().lower())
        finally:
            db.close()
    except Exception:
        pass
    return sorted(names, key=len, reverse=True)


def check_role_and_privacy_guard(
    message: str,
    user_role: str = "EMPLOYEE",
    user_name: str = "User",
    assistant_mode: str = "AI"
) -> tuple[bool, str, list[str]]:
    """
    Comprehensive 3-Layer Enterprise Security & Individual Privacy Guard:
    1. INTERN BOUNDARY:
       - Interns CANNOT use the Company RAG Vault for internal company data.
       - Interns CANNOT access Full-Time Employee Policies, Leave/Benefits, Equipment Allowance,
         Manager Playbooks, HR Compensation Grids, or Company Employee Databases.
    2. EMPLOYEE BOUNDARY:
       - Employees CANNOT access Manager Leadership & Appraisal Playbooks (PIP, merit bonus pools, squad budgets)
         or HR Master Compensation Grids (L1-L4 salary bands, ESOPs, severance, termination protocols).
    3. MANAGER BOUNDARY:
       - Managers CANNOT access HR-Only Executive Compensation & Severance Master Grids.
    4. INDIVIDUAL EMPLOYEE PRIVACY ISOLATION:
       - Every Employee and Intern has strict personal privacy. No Employee or Intern may query
         another colleague's salary, stipend, tasks, working hours, KYC documents, or personal profile.
    """
    role = (user_role or "EMPLOYEE").upper()
    msg_lower = message.lower()
    caller_lower = (user_name or "").strip().lower()

    # Default caller names by role if generic
    if not caller_lower or caller_lower in ("user", "guest", "employee", "intern"):
        default_names = {
            "INTERN": "ananya roy",
            "EMPLOYEE": "rahul verma",
            "MANAGER": "vikram mehta",
            "HR": "priya sharma",
            "ADMIN": "system admin"
        }
        caller_lower = default_names.get(role, "rahul verma")

    # ------------------------------------------------------------------
    # LAYER 1: INDIVIDUAL EMPLOYEE PRIVACY ISOLATION (For Intern & Employee)
    # ------------------------------------------------------------------
    if role in ("INTERN", "EMPLOYEE"):
        all_names = _get_all_known_personnel_names()
        caller_tokens = set(caller_lower.split())

        for other_name in all_names:
            other_tokens = set(other_name.split())
            # Skip if this is the caller's own name
            if other_name == caller_lower or (caller_tokens and caller_tokens == other_tokens):
                continue
            # Also allow mentioning their manager's name only when asking "who is my manager/mentor"
            if other_name in msg_lower:
                private_intent_keywords = [
                    "salary", "stipend", "pay", "ctc", "compensation", "task", "tasks",
                    "working hour", "working time", "attendance", "clock", "document",
                    "resume", "pan", "aadhaar", "bank", "address", "phone", "email",
                    "profile", "appraisal", "rating", "performance", "leave", "certificate",
                    "offer letter", "workload", "progress", "tenure", "details", "record", "info"
                ]
                if any(pk in msg_lower for pk in private_intent_keywords) or len(msg_lower.split()) <= 6:
                    return (
                        False,
                        (
                            f"### 🔒 Individual Employee Privacy Protection\n\n"
                            f"**Access Denied:** Under the **RAGNIFY Enterprise Data Privacy Policy** "
                            f"(`RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf`), every employee and intern has a strictly "
                            f"isolated personal privacy boundary.\n\n"
                            f"- **Logged-In Identity:** **{user_name}** (`{role}`)\n"
                            f"- **Requested Subject:** **{other_name.title()}**\n"
                            f"- **Privacy Rule:** You are only authorized to query **your own** personal tasks, working hours, "
                            f"compensation, and profile records. Cross-employee inspection of salaries, tasks, attendance logs, "
                            f"or KYC documents is strictly prohibited."
                        ),
                        ["RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf", "Individual Privacy Guard"]
                    )

        # Also block bulk/all-employee private data harvesting by Interns or Employees
        bulk_private_patterns = [
            "all employees salary", "all employee salaries", "everyone's salary", "colleagues salary",
            "other employees salary", "all employees tasks", "all employees documents",
            "salary of all", "list all salaries", "payroll list", "employee database dump"
        ]
        if any(bp in msg_lower for bp in bulk_private_patterns):
            return (
                False,
                (
                    f"### 🔒 Individual Employee Privacy & Data Isolation\n\n"
                    f"**Access Denied:** Bulk inspection of other employees' salaries, tasks, or private records is "
                    f"strictly restricted. As **{user_name}** (`{role}`), you may only access your own personal employment data."
                ),
                ["RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf"]
            )

    # ------------------------------------------------------------------
    # LAYER 2: INTERN ROLE BOUNDARY (No Company-Internal / FTE / Manager / HR Data)
    # ------------------------------------------------------------------
    if role == "INTERN":

        intern_company_restricted_keywords = [
            # Full-time employee policies & benefits
            "full-time leave", "full time leave", "18 casual", "12 sick", "equipment allowance",
            "5,500", "5500", "health insurance", "5,00,000", "family floater", "maternity",
            "paternity", "work from anywhere", "probation confirmation", "employee handbook",
            "company leave policy", "employee benefits", "learning budget", "25,000",
            # Manager & HR confidential
            "executive salary", "compensation grid", "salary band", "l1", "l2", "l3", "l4",
            "severance", "equity", "esop", "performance appraisal", "appraisal rating",
            "merit bonus", "pip", "performance improvement plan", "squad budget", "1,50,000",
            "confidential payroll", "termination protocol", "manager playbook", "hr compensation",
            "company financials", "company revenue", "all employees", "employee list"
        ]
        for kw in intern_company_restricted_keywords:
            if kw in msg_lower:
                return (
                    False,
                    (
                        "### 🔒 Company Data Access Restricted (Intern Clearance)\n\n"
                        "**Security Policy Notice:** Internal company policies, full-time employee benefit handbooks, "
                        "managerial appraisal playbooks, and HR compensation grids are accessible **only to Employee, Manager, "
                        "HR, and Admin personnel**.\n\n"
                        "#### ✅ What You Can Access as an Intern (`" + user_name + "`):\n"
                        "- **Internship Handbook (`RAGNIFY_Internship_Handbook_2026.pdf`):** Stipend (**₹30,000/month**), "
                        "**92-day** tenure roadmap, **1 paid leave/month**, and 3-stage Certificate unlock rules.\n"
                        "- **Engineering Standards (`RAGNIFY_Engineering_And_SaaS_Architecture_Guide_2026.pdf`):** Coding, Git, and architecture guidelines.\n"
                        "- **Your Personal Records:** Your own assigned tasks, daily working hours, and mentor details."
                    ),
                    ["RAGNIFY_Internship_Handbook_2026.pdf", "RBAC Policy Guard"]
                )

    # ------------------------------------------------------------------
    # LAYER 3: EMPLOYEE ROLE BOUNDARY (No Intern Handbook, Manager Playbooks, or HR Confidential Docs)
    # ------------------------------------------------------------------
    if role == "EMPLOYEE":
        employee_restricted_intern_docs = [
            "intern handbook", "internship handbook", "intern stipend", "intern policy",
            "intern guidelines", "intern leave", "intern tenure", "ppo conversion", "ppo rule"
        ]
        for kw in employee_restricted_intern_docs:
            if kw in msg_lower:
                return (
                    False,
                    (
                        "### 🔒 Document Clearance Restriction (Internship Program Handbook)\n\n"
                        f"**Access Denied:** Your account clearance is **`EMPLOYEE`** (**{user_name}**). "
                        f"The **RAGNIFY Official Internship Program Handbook** (`RAGNIFY_Internship_Handbook_2026.pdf`) "
                        f"is restricted to **Interns**, their supervising **Managers**, and **HR / Admin** personnel.\n\n"
                        f"- **Restricted Document:** `RAGNIFY_Internship_Handbook_2026.pdf`\n"
                        f"- **Reason:** Full-time employees are not permitted to view or query intern handbooks or stipend frameworks.\n\n"
                        f"#### ✅ Documents Accessible Under Your `EMPLOYEE` Clearance:\n"
                        f"1. **`RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf`** *(Leave policy, ₹5,500 equipment allowance, ₹5L health insurance, hybrid work)*\n"
                        f"2. **`RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf`** *(Security & privacy compliance)*\n"
                        f"3. **`RAGNIFY_Engineering_And_SaaS_Architecture_Guide_2026.pdf`** *(Technical & sprint workflow)*\n"
                        f"4. **Your Personal Employment Profile, Tasks & Working Hours**"
                    ),
                    ["RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf", "RBAC Clearance Guard"]
                )

        employee_restricted_manager_hr = [
            # Manager Playbook topics
            "manager playbook", "leadership playbook", "appraisal rubric", "appraisal rating",
            "merit bonus pool", "performance improvement plan", "pip protocol", "45-day pip",
            "squad budget", "1,50,000", "discretionary team", "workload balancing threshold",
            # HR Confidential topics
            "compensation grid", "salary band", "salary structure", "band l1", "band l2",
            "band l3", "band l4", "esop matrix", "executive salary", "executive compensation",
            "confidential payroll", "severance package", "termination protocol", "disciplinary governance",
            "hr master compensation", "cross-department salary"
        ]
        for kw in employee_restricted_manager_hr:
            if kw in msg_lower:
                is_mgr_doc = any(m in msg_lower for m in ["manager", "playbook", "pip", "squad budget", "workload", "appraisal rubric"])
                restricted_doc = (
                    "RAGNIFY_Manager_Leadership_And_Appraisal_Playbook_2026.pdf (Manager, HR & Admin Only)"
                    if is_mgr_doc
                    else "RAGNIFY_HR_Compensation_Grids_And_Executive_Governance_2026.pdf (HR & Admin Only)"
                )
                return (
                    False,
                    (
                        "### 🔒 Document Clearance Restriction (Manager / HR Confidential)\n\n"
                        f"**Access Denied:** Your account clearance is **`EMPLOYEE`** (**{user_name}**). "
                        f"The information you requested belongs to a restricted governance document:\n\n"
                        f"- **Restricted Source:** `{restricted_doc}`\n"
                        f"- **Required Clearance:** `MANAGER`, `HR`, or `ADMIN`\n\n"
                        f"#### ✅ Documents Accessible Under Your `EMPLOYEE` Clearance:\n"
                        f"1. **`RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf`** *(Leave policy, ₹5,500 equipment allowance, ₹5L health insurance, hybrid work)*\n"
                        f"2. **`RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf`** *(Security & privacy compliance)*\n"
                        f"3. **`RAGNIFY_Engineering_And_SaaS_Architecture_Guide_2026.pdf`** *(Technical & sprint workflow)*\n"
                        f"4. **Your Personal Employment Profile, Tasks & Working Hours**"
                    ),
                    ["RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf", "RBAC Clearance Guard"]
                )

    # ------------------------------------------------------------------
    # LAYER 4: MANAGER ROLE BOUNDARY (No HR-Only Executive Payroll / Severance Grids)
    # ------------------------------------------------------------------
    if role == "MANAGER":
        manager_restricted_hr_only = [
            "executive payroll master", "band l4", "director salary", "vp salary",
            "severance package", "termination protocol", "hr master compensation grid",
            "disciplinary termination governance"
        ]
        for kw in manager_restricted_hr_only:
            if kw in msg_lower:
                return (
                    False,
                    (
                        "### 🔒 HR Executive Governance Restriction\n\n"
                        f"**Access Denied:** While your **`MANAGER`** clearance (**{user_name}**) grants full access to "
                        f"`RAGNIFY_Manager_Leadership_And_Appraisal_Playbook_2026.pdf` and your team's operational metrics, "
                        f"the **HR Master Compensation & Severance Governance Grid** "
                        f"(`RAGNIFY_HR_Compensation_Grids_And_Executive_Governance_2026.pdf`) is strictly restricted to **HR and Admin** roles."
                    ),
                    ["RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf", "HR Governance Guard"]
                )

    return True, "", []


def build_live_role_scoped_db_context(user_role: str = "EMPLOYEE", user_name: str = "User") -> str:
    """
    Build real-time PostgreSQL workforce & personal context strictly scoped to the user's
    role and personal identity so each user has complete privacy while getting ChatGPT-level accuracy.
    """
    role = (user_role or "EMPLOYEE").upper()
    caller_name = (user_name or "").strip()

    if not caller_name or caller_name.lower() in ("user", "guest", "employee", "intern", "manager", "hr", "admin"):
        defaults = {
            "INTERN": "Ananya Roy",
            "EMPLOYEE": "Rahul Verma",
            "MANAGER": "Vikram Mehta",
            "HR": "Priya Sharma",
            "ADMIN": "System Admin"
        }
        caller_name = defaults.get(role, "Rahul Verma")

    lines = [f"=== LIVE RAGNIFY SAAS PLATFORM DATABASE CONTEXT (Scoped for {caller_name} | Role: {role}) ==="]

    try:
        from database import SessionLocal
        import models
        db = SessionLocal()
        try:
            if role == "INTERN":
                # Strictly ONLY this intern's personal data
                lines.append(
                    f"• Personal Intern Profile (Private to {caller_name}):\n"
                    f"  - Candidate ID: INT-201 | Name: {caller_name} | Role: Frontend Development Intern\n"
                    f"  - Department: Engineering & Product Innovation | Assigned Mentor: Vikram Mehta\n"
                    f"  - Monthly Stipend: ₹30,000 / month (Direct Bank Transfer)\n"
                    f"  - Tenure Period: Aug 01, 2026 – Oct 31, 2026 (92 Total Days, 68 Days Completed, 74% Progress)\n"
                    f"  - Certificate Status: Preview Ready / Unlocks upon 100% tenure or HR sign-off."
                )
                # Find tasks assigned to this intern
                emp = db.query(models.Employee).filter(models.Employee.full_name.ilike(f"%{caller_name.split()[0]}%")).first()
                if emp:
                    tasks = db.query(models.Task).filter(models.Task.assigned_employee_id == emp.employee_id).all()
                    if tasks:
                        t_strs = [f"    * [{t.status}] {t.task_title} (Priority: {t.priority})" for t in tasks]
                        lines.append("• Your Assigned Internship Tasks:\n" + "\n".join(t_strs))

            elif role == "EMPLOYEE":
                # Strictly ONLY this employee's personal data
                emp = db.query(models.Employee).filter(models.Employee.full_name.ilike(f"%{caller_name.split()[0]}%")).first()
                if emp:
                    tasks = db.query(models.Task).filter(models.Task.assigned_employee_id == emp.employee_id).all()
                    done_c = sum(1 for t in tasks if (t.status or "").upper() == "COMPLETED")
                    pct = round((done_c / len(tasks)) * 100) if tasks else 100
                    lines.append(
                        f"• Personal Employee Profile (Private to {emp.full_name}):\n"
                        f"  - Employee ID: {emp.employee_id} | Name: {emp.full_name} | Role: {emp.designation or 'Senior Software Engineer'}\n"
                        f"  - Department: {emp.department} | Email: {emp.email}\n"
                        f"  - Personal Task Progress: {done_c}/{len(tasks)} Tasks Completed ({pct}%)"
                    )
                    if tasks:
                        t_strs = [f"    * [{t.status}] {t.task_title} (Priority: {t.priority})" for t in tasks]
                        lines.append("• Your Personal Assigned Tasks:\n" + "\n".join(t_strs))
                else:
                    lines.append(
                        f"• Personal Employee Profile (Private to {caller_name}):\n"
                        f"  - Name: {caller_name} | Role: Senior ML Engineer | Department: AI & Data Science\n"
                        f"  - Reporting Manager: Vikram Mehta | Leave Balance: 18 Casual Leaves, 12 Sick Leaves\n"
                        f"  - Equipment Allowance Eligibility: ₹5,500 within 30 days of joining."
                    )

            elif role == "MANAGER":
                # Manager sees team members, task progress, and workload metrics
                emps = db.query(models.Employee).all()
                tasks = db.query(models.Task).all()
                total_t = len(tasks)
                comp_t = sum(1 for t in tasks if (t.status or "").upper() == "COMPLETED")
                prog_pct = round((comp_t / total_t) * 100) if total_t else 0
                lines.append(
                    f"• Engineering Manager Team Overview (Manager: {caller_name}):\n"
                    f"  - Total Managed Workforce: {len(emps)} Team Members | Total Tasks: {total_t} ({comp_t} Completed, {prog_pct}% Auto-Calculated Progress)"
                )
                team_rows = []
                for e in emps[:12]:
                    e_tasks = [t for t in tasks if t.assigned_employee_id == e.employee_id]
                    e_done = sum(1 for t in e_tasks if (t.status or "").upper() == "COMPLETED")
                    e_pct = round((e_done / len(e_tasks)) * 100) if e_tasks else 0
                    team_rows.append(f"  - {e.full_name} ({e.designation or 'Engineer'}, {e.department}): {e_done}/{len(e_tasks)} tasks completed ({e_pct}%)")
                if team_rows:
                    lines.append("• Team Member Task & Workload Breakdown:\n" + "\n".join(team_rows))

            elif role in ("HR", "ADMIN"):
                # HR & Admin see complete enterprise governance metrics
                emps = db.query(models.Employee).all()
                cands = db.query(models.CandidateProfile).all()
                tasks = db.query(models.Task).all()
                hrvs = {v.candidate_id: v for v in db.query(models.HRVerification).all()}
                interns_c = sum(1 for c in cands if c.candidate_type == "Intern")
                ftes_c = sum(1 for c in cands if c.candidate_type == "Employee")
                pending_apps = sum(1 for c in cands if (hrvs.get(c.candidate_id).overall_onboarding_status if hrvs.get(c.candidate_id) else "PENDING").upper() in ("PENDING", "UNDER_REVIEW", "IN_PROGRESS"))
                lines.append(
                    f"• Live HR & Enterprise Governance Master Summary (Authorized for {caller_name} - {role}):\n"
                    f"  - Active Core Employees Table: {len(emps)} | Onboarding Candidate Profiles: {len(cands)} ({ftes_c} Employees, {interns_c} Interns)\n"
                    f"  - Pending / In-Review Onboarding Applications: {pending_apps}\n"
                    f"  - Total Tracked Engineering Tasks: {len(tasks)}"
                )
                cand_list = [
                    f"  - {c.candidate_id}: {c.full_name} ({c.candidate_type}) — Status: {(hrvs.get(c.candidate_id).overall_onboarding_status if hrvs.get(c.candidate_id) else 'PENDING')}"
                    for c in cands[:15]
                ]
                if cand_list:
                    lines.append("• Candidate & Onboarding Registry Snapshot:\n" + "\n".join(cand_list))
        finally:
            db.close()
    except Exception as e:
        print(f"Warning building live DB context: {e}")

    return "\n\n".join(lines)


ROLE_POLICIES_CONFIG = {
    "INTERN": [
        {"title": "Internship Stipend Policy", "desc": "Monthly stipend of ₹30,000/month, payment on 1st of every month & direct deposit."},
        {"title": "92-Day Tenure Roadmap", "desc": "Complete 3-stage milestone schedule (Days 1–30 Foundation, Days 31–60 Projects, Days 61–92 Delivery)."},
        {"title": "Intern Leave & Attendance", "desc": "Entitlement of 1 paid leave per month, daily clock-in rules & sprint timings."},
        {"title": "3-Stage Certificate Unlock", "desc": "Milestone evaluation rules for Internship Certificate, Letter of Recommendation, and Completion Sign-off."},
        {"title": "PPO Conversion Criteria", "desc": "Performance thresholds & mentor review rubrics for full-time software engineer conversion."},
        {"title": "Engineering & Coding Standards", "desc": "Git workflow, branch naming, PR reviews, and SaaS architecture standards."}
    ],
    "MANAGER": [
        {"title": "Performance Appraisal & Bonus Rubric", "desc": "1–5 rating scale, 8%–22% merit bonus pool distribution, and review cycles."},
        {"title": "45-Day PIP Protocol", "desc": "Performance Improvement Plan timelines, weekly coaching checkpoints, and evaluation criteria."},
        {"title": "Squad Discretionary Budget", "desc": "₹1,50,000 quarterly squad budget for team offsites, hackathons, and certifications."},
        {"title": "Team Workload Balancing Guidelines", "desc": "Optimal 3–5 active tasks threshold to prevent engineer burnout."},
        {"title": "Annual Leave Policy", "desc": "Core employee entitlements (18 casual leaves, 12 sick leaves, carry-forward, encashment)."},
        {"title": "Equipment Allowance Policy (₹5,500)", "desc": "₹5,500 new joiner home office equipment reimbursement guidelines."},
        {"title": "Health Insurance & Medical Coverage", "desc": "₹5,00,000 medical floater coverage details."}
    ],
    "HR": [
        {"title": "Annual Leave Policy", "desc": "Full-time employee leaves (18 casual, 12 sick, carry-forward, encashment)."},
        {"title": "Equipment Allowance Policy (₹5,500)", "desc": "Home office stipend rules and verification criteria."},
        {"title": "L1–L4 Salary & ESOP Bands", "desc": "Master compensation benchmarks, bands, and equity vest schedules."},
        {"title": "Severance & Termination Protocol", "desc": "Disciplinary governance, notice pay, and statutory exit clearances."},
        {"title": "Internship Program Governance", "desc": "92-day roadmap, ₹30,000 stipend, and 3-stage certificate issuance."},
        {"title": "Onboarding Document Verification", "desc": "KYC, PAN, Aadhaar, degree, and previous employment verification."}
    ],
    "ADMIN": [
        {"title": "Annual Leave Policy", "desc": "Full-time employee leaves (18 casual, 12 sick, carry-forward, encashment)."},
        {"title": "Equipment Allowance Policy (₹5,500)", "desc": "Home office stipend rules and verification criteria."},
        {"title": "L1–L4 Salary & ESOP Bands", "desc": "Master compensation benchmarks, bands, and equity vest schedules."},
        {"title": "Severance & Termination Protocol", "desc": "Disciplinary governance, notice pay, and statutory exit clearances."},
        {"title": "Internship Program Governance", "desc": "92-day roadmap, ₹30,000 stipend, and 3-stage certificate issuance."},
        {"title": "Onboarding Document Verification", "desc": "KYC, PAN, Aadhaar, degree, and previous employment verification."}
    ],
    "EMPLOYEE": [
        {"title": "Annual Leave Policy", "desc": "18 Paid Casual Leaves, 10-day carry forward, and year-end encashment."},
        {"title": "Sick & Emergency Leave Policy", "desc": "12 Paid Sick Leaves per year with streamlined medical notice."},
        {"title": "Equipment Allowance Policy (₹5,500)", "desc": "One-time tech stipend for your home workstation setup."},
        {"title": "Health Insurance & Medical Coverage", "desc": "Comprehensive ₹5,00,000 family floater health plan."},
        {"title": "Hybrid & Remote Work (WFH) Guidelines", "desc": "Work-from-home schedule, core hours, and attendance check-ins."},
        {"title": "Learning & Skill Development Budget", "desc": "Annual ₹25,000 professional certification and book stipend."},
        {"title": "IT Security & Device Data Privacy", "desc": "Mandatory 2FA, data encryption, and clean desk guidelines."}
    ]
}


def handle_socratic_policy_dialogue(
    message: str,
    user_role: str = "EMPLOYEE",
    user_name: str = "User"
) -> Optional[dict]:
    """
    Teacher/Mentor Socratic Policy Classifier & Official Policy Notification Engine:
    1. Unavailable Data: If user asks about data/perks not in company records, apologize and offer available policies.
    2. Broad Inquiry: If user asks about general policies/info, say "I have these policies available for you. Which one would you like to read?" with clickable options.
    3. Exact Policy: Deliver full official notification with entitlements & follow-up clickable tabs.
    """
    msg_lower = (message or "").strip().lower()
    role = (user_role or "EMPLOYEE").upper()
    name = user_name or "Colleague"

    role_config = ROLE_POLICIES_CONFIG.get(role, ROLE_POLICIES_CONFIG["EMPLOYEE"])
    role_action_titles = [item["title"] for item in role_config]

    # ------------------------------------------------------------------
    # A. UNAVAILABLE DATA / NON-EXISTENT POLICIES IN COMPANY RECORDS
    # ------------------------------------------------------------------
    unavailable_patterns = [
        "pet insurance", "pet policy", "pets", "pet cover", "dog insurance", "cat insurance",
        "crypto", "cryptocurrency", "bitcoin", "eth", "ethereum", "token grant",
        "swimming pool", "pool facility", "swimming",
        "flight ticket", "flight tickets", "airline ticket", "airfare", "travel ticket", "flight reimbursement",
        "car lease", "car allowance", "company car", "vehicle policy", "petrol allowance", "fuel reimbursement",
        "unlimited sabbatical", "sabbatical leave", "sabbatical policy", "sabbatical",
        "gym", "gym membership", "fitness allowance", "health club",
        "personal loan", "loan policy", "salary advance loan", "company loan",
        "credit card", "corporate card", "company credit card",
        "free lunch", "free food", "canteen meal", "meal voucher", "food coupon", "zomato", "swiggy",
        "gaming room", "playstation", "ps5", "xbox", "game room", "recreation room",
        "smoking room", "smoke break", "smoking policy", "tobacco",
        "dress code", "uniform", "clothing allowance",
        "overtime pay", "overtime rate", "night shift allowance"
    ]
    if any(p in msg_lower for p in unavailable_patterns):
        options_markdown = "\n".join([f"- [👉 {t}]" for t in role_action_titles[:5]])
        return {
            "answer": (
                f"### ℹ️ Record Not Found\n\n"
                f"Sorry, this information does not exist in our company records.\n\n"
                f"Instead of this, would you like to know about anything else? Under your **`{role}`** clearance, I have the following official policies available for you:\n\n"
                f"{options_markdown}\n\n"
                f"---\n"
                f"👉 **Which one would you like to explore? Click an option above or below:**"
            ),
            "sources": [f"RAGNIFY Official Policy Index ({role})"],
            "suggested_actions": role_action_titles[:5]
        }

    # ------------------------------------------------------------------
    # B. EXACT POLICY: Annual Leave / Paid Vacation Policy
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in [
        "annual policy", "annual leave", "annual leaves", "paid leave", "casual leave",
        "vacation policy", "carry forward", "leave encashment"
    ]):
        if role == "INTERN":
            return {
                "answer": (
                    f"### 📢 Official Policy Notification: Intern Paid Leave & Attendance (2026)\n\n"
                    f"**Source Document:** `RAGNIFY_Internship_Handbook_2026.pdf`\n"
                    f"**Authorized Clearance:** `INTERN` ({name})\n\n"
                    f"#### 📌 Core Entitlements & Attendance Rules:\n"
                    f"- **Monthly Paid Leave:** Interns are entitled to **1 Paid Leave per month** (accumulates to 3 paid leaves over the 92-day program).\n"
                    f"- **Working Hours & Clock:** Standard sprint schedule is **9:30 AM – 6:30 PM (IST)**, Monday through Friday, with daily task clock-in.\n"
                    f"- **Application Process:** Request leave at least **24 hours in advance** through the RAGNIFY Portal for Mentor/Manager approval.\n"
                    f"- **Stipend Protection:** Authorized monthly leave does not cause any deduction from your **₹30,000/month** stipend.\n\n"
                    f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                    f"Now that you've reviewed the Intern Leave Policy, what would you like to explore next? Click an option below:\n"
                    f"- [👉 Internship Stipend Policy]\n"
                    f"- [👉 92-Day Tenure Roadmap]\n"
                    f"- [👉 3-Stage Certificate Unlock]\n"
                    f"- [👉 PPO Conversion Criteria]"
                ),
                "sources": ["RAGNIFY_Internship_Handbook_2026.pdf"],
                "suggested_actions": [
                    "Internship Stipend Policy",
                    "92-Day Tenure Roadmap",
                    "3-Stage Certificate Unlock",
                    "PPO Conversion Criteria"
                ]
            }
        else:
            return {
                "answer": (
                    f"### 📢 Official Policy Notification: Annual Paid Leave & Vacation (2026)\n\n"
                    f"**Source Document:** `RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf`\n"
                    f"**Authorized Clearance:** `{role}` ({name})\n\n"
                    f"#### 📌 Core Entitlements & Rules:\n"
                    f"- **Annual Casual Leave:** **18 Paid Days** per calendar year, credited pro-rata at **1.5 days/month**.\n"
                    f"- **Paid Sick Leave:** **12 Days** dedicated for medical recovery & health emergencies.\n"
                    f"- **National & Festival Holidays:** **10 Gazetted Holidays** published annually by HR.\n"
                    f"- **Carry-Forward Provision:** Up to **10 unused days** can be carried forward into the subsequent calendar year.\n"
                    f"- **Encashment Benefit:** Unused leave balance beyond the 10-day carry-forward cap is encashable at year-end based on base pay.\n"
                    f"- **Advance Notice Requirement:** Minimum **3 working days** advance notice required for planned leave of 2 or more consecutive days.\n"
                    f"- **Approval Protocol:** Apply directly via **RAGNIFY Portal** $\rightarrow$ Line Manager approves within **24 hours** $\rightarrow$ Automatic HR synchronization.\n\n"
                    f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                    f"Now that you understand the Annual Leave Policy, which related module would you like to examine next? Click an option below or request a formal report:\n"
                    f"- [👉 Sick & Emergency Leave Policy]\n"
                    f"- [👉 Equipment Allowance Policy (₹5,500)]\n"
                    f"- [👉 Health Insurance & Medical Coverage]\n"
                    f"- [👉 Generate Leave Policy PDF]"
                ),
                "sources": ["RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf"],
                "suggested_actions": [
                    "Sick & Emergency Leave Policy",
                    "Equipment Allowance Policy (₹5,500)",
                    "Health Insurance & Medical Coverage",
                    "Generate Leave Policy PDF"
                ]
            }

    # ------------------------------------------------------------------
    # D. EXACT POLICY: Sick Leave Policy
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["sick policy", "sick leave", "medical leave", "health emergency"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Sick & Emergency Medical Leave (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf`\n"
                f"**Authorized Clearance:** `{role}` ({name})\n\n"
                f"#### 📌 Sick Leave Provisions:\n"
                f"- **Allotment:** **12 Paid Sick Days** per calendar year (1 day credited each month).\n"
                f"- **Certification:** Medical practitioner certificate is required for sick leave exceeding **2 consecutive business days**.\n"
                f"- **Emergency Notification:** In case of sudden illness, inform your manager or log into the portal before **10:00 AM** on the day of absence.\n"
                f"- **Non-Encashment:** Sick leaves are intended purely for health recovery and do not lapse into cash encashment.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Would you like to review health coverage or return to leave options? Click an option below:\n"
                f"- [👉 Annual Leave Policy]\n"
                f"- [👉 Health Insurance & Medical Coverage]\n"
                f"- [👉 Equipment Allowance Policy (₹5,500)]\n"
                f"- [👉 Generate Leave Policy PDF]"
            ),
            "sources": ["RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf"],
            "suggested_actions": [
                "Annual Leave Policy",
                "Health Insurance & Medical Coverage",
                "Equipment Allowance Policy (₹5,500)",
                "Generate Leave Policy PDF"
            ]
        }

    # ------------------------------------------------------------------
    # E. EXACT POLICY: Equipment Allowance
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["equipment", "tech allowance", "stipend for monitor", "home office allowance", "5500", "5,500"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Home Office & Equipment Allowance (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf`\n"
                f"**Authorized Clearance:** `{role}` ({name})\n\n"
                f"#### 📌 Equipment Reimbursement Guidelines:\n"
                f"- **Reimbursement Cap:** Up to **₹5,500 (one-time reimbursement)** for remote & hybrid workplace enablement.\n"
                f"- **Eligible Items:** Ergonomic accessories, high-speed Wi-Fi router, external keyboard/mouse, monitor arms, noise-canceling headsets.\n"
                f"- **Submission Timeline:** Expense receipts must be submitted via the Portal within **30 days of joining**.\n"
                f"- **Disbursement:** Approved claims are credited in the subsequent payroll cycle.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which module shall we explore next? Click an option below:\n"
                f"- [👉 Annual Leave Policy]\n"
                f"- [👉 Health Insurance & Medical Coverage]\n"
                f"- [👉 Hybrid & Remote Work (WFH) Guidelines]\n"
                f"- [👉 Generate Policy PDF Report]"
            ),
            "sources": ["RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf"],
            "suggested_actions": [
                "Annual Leave Policy",
                "Health Insurance & Medical Coverage",
                "Hybrid & Remote Work (WFH) Guidelines",
                "Generate Policy PDF Report"
            ]
        }

    # ------------------------------------------------------------------
    # F. EXACT POLICY: Health Insurance & Medical Coverage
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["health insurance", "insurance policy", "medical insurance", "5,00,000", "500000", "family floater", "mediclaim"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Group Health Insurance & Medical Floater (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf`\n"
                f"**Authorized Clearance:** `{role}` ({name})\n\n"
                f"#### 📌 Coverage Entitlements:\n"
                f"- **Sum Insured:** **₹5,00,000 Family Floater** coverage for the employee, spouse, and up to 2 dependent children.\n"
                f"- **Cashless Hospitalization:** Instant pre-authorization across **6,000+ empaneled hospitals** nationwide.\n"
                f"- **Maternity Coverage:** Normal and C-section delivery covered up to **₹50,000**, with day-one infant protection.\n"
                f"- **Pre & Post Hospitalization:** 30 days prior and 60 days post-discharge medical expenses covered.\n"
                f"- **Emergency Helpdesk:** 24/7 dedicated insurer TPA desk accessible directly via the RAGNIFY Portal.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which related benefit would you like to review next? Click an option below:\n"
                f"- [👉 Annual Leave Policy]\n"
                f"- [👉 Sick & Emergency Leave Policy]\n"
                f"- [👉 Equipment Allowance Policy (₹5,500)]"
            ),
            "sources": ["RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf"],
            "suggested_actions": [
                "Annual Leave Policy",
                "Sick & Emergency Leave Policy",
                "Equipment Allowance Policy (₹5,500)"
            ]
        }

    # ------------------------------------------------------------------
    # G. EXACT POLICY: Hybrid & Remote Work (WFH)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["hybrid", "wfh", "remote work", "work from home", "remote policy"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Hybrid & Remote Work Guidelines (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf`\n"
                f"**Authorized Clearance:** `{role}` ({name})\n\n"
                f"#### 📌 Hybrid Work Guidelines:\n"
                f"- **Schedule Flexibility:** Employees may work remotely up to **2 days per week** (typically Tuesday & Thursday, or as aligned with your Manager).\n"
                f"- **Core Collaboration Hours:** Online presence on Slack/Teams is required between **10:00 AM – 5:00 PM IST**.\n"
                f"- **Connectivity Standard:** Stable broadband connection (minimum 50 Mbps recommended) with enterprise VPN enabled.\n"
                f"- **Workstation Support:** Remember to claim your one-time **₹5,500** equipment reimbursement for your home desk setup.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which module shall we examine next? Click an option below:\n"
                f"- [👉 Equipment Allowance Policy (₹5,500)]\n"
                f"- [👉 Annual Leave Policy]\n"
                f"- [👉 IT Security & Device Data Privacy]"
            ),
            "sources": ["RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf"],
            "suggested_actions": [
                "Equipment Allowance Policy (₹5,500)",
                "Annual Leave Policy",
                "IT Security & Device Data Privacy"
            ]
        }

    # ------------------------------------------------------------------
    # H. EXACT POLICY: Learning & Skill Development Budget
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["learning budget", "skill development", "25000", "25,000", "certification budget", "training allowance"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Professional Learning & Certification Budget (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf`\n"
                f"**Authorized Clearance:** `{role}` ({name})\n\n"
                f"#### 📌 Learning Stipend Details:\n"
                f"- **Annual Entitlement:** **₹25,000 per fiscal year** per full-time engineer.\n"
                f"- **Eligible Expenses:** Industry certifications (AWS, GCP, Azure, CKA, Scrum), technical books, conference registrations, and accredited online courses.\n"
                f"- **Approval & Reimbursement:** Get prior approval from your Engineering Manager and submit completion certificates/invoices for full reimbursement.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Would you like to examine equipment benefits or leave policies next?\n"
                f"- [👉 Equipment Allowance Policy (₹5,500)]\n"
                f"- [👉 Annual Leave Policy]\n"
                f"- [👉 Hybrid & Remote Work (WFH) Guidelines]"
            ),
            "sources": ["RAGNIFY_Employee_Handbook_And_Benefits_2026.pdf"],
            "suggested_actions": [
                "Equipment Allowance Policy (₹5,500)",
                "Annual Leave Policy",
                "Hybrid & Remote Work (WFH) Guidelines"
            ]
        }

    # ------------------------------------------------------------------
    # I. EXACT POLICY: IT Security & Device Data Privacy
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["it security", "data privacy", "security policy", "2fa", "mfa", "clean desk"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: IT Security & Enterprise Data Protection (2026)\n\n"
                f"**Source Document:** `RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf`\n"
                f"**Authorized Clearance:** `{role}` ({name})\n\n"
                f"#### 📌 Mandatory Security Protocols:\n"
                f"- **Two-Factor Authentication (2FA):** Mandatory Mobile OTP / Authenticator on all enterprise logins.\n"
                f"- **Disk Encryption:** Full-disk BitLocker / FileVault encryption enabled on all development workstations.\n"
                f"- **Auto-Lock Standard:** Workstations must auto-lock after **5 minutes of inactivity**.\n"
                f"- **Data Protection:** No company code or customer data may be uploaded to unauthorized personal cloud drives or external AI platforms.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which area would you like to explore next?\n"
                f"- [👉 Hybrid & Remote Work (WFH) Guidelines]\n"
                f"- [👉 Equipment Allowance Policy (₹5,500)]\n"
                f"- [👉 Annual Leave Policy]"
            ),
            "sources": ["RAGNIFY_IT_Security_And_Data_Privacy_Policy_2026.pdf"],
            "suggested_actions": [
                "Hybrid & Remote Work (WFH) Guidelines",
                "Equipment Allowance Policy (₹5,500)",
                "Annual Leave Policy"
            ]
        }

    # ------------------------------------------------------------------
    # J. EXACT POLICY: Internship Stipend Policy (Intern Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["internship stipend", "intern stipend", "stipend policy", "30,000", "30000", "stipend"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Internship Monthly Stipend (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Internship_Handbook_2026.pdf`\n"
                f"**Authorized Clearance:** `INTERN` ({name})\n\n"
                f"#### 📌 Stipend Entitlements & Payroll Schedule:\n"
                f"- **Monthly Stipend:** **₹30,000 per month** (Direct bank transfer).\n"
                f"- **Disbursement Date:** Credited on the **1st business day of every calendar month**.\n"
                f"- **Attendance & Leaves:** 1 authorized paid leave per month is permitted without any deduction from your stipend.\n"
                f"- **High-Performance Milestone Bonus:** Up to **₹5,000 bonus** upon successful Day 60 milestone sign-off by your Mentor.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"What would you like to review next? Click an option below:\n"
                f"- [👉 92-Day Tenure Roadmap]\n"
                f"- [👉 Intern Leave & Attendance]\n"
                f"- [👉 3-Stage Certificate Unlock]\n"
                f"- [👉 PPO Conversion Criteria]"
            ),
            "sources": ["RAGNIFY_Internship_Handbook_2026.pdf"],
            "suggested_actions": [
                "92-Day Tenure Roadmap",
                "Intern Leave & Attendance",
                "3-Stage Certificate Unlock",
                "PPO Conversion Criteria"
            ]
        }

    # ------------------------------------------------------------------
    # K. EXACT POLICY: 92-Day Tenure Roadmap (Intern Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["92-day", "92 day", "tenure roadmap", "milestone roadmap", "roadmap"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: 92-Day Internship Tenure Roadmap (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Internship_Handbook_2026.pdf`\n"
                f"**Authorized Clearance:** `INTERN` ({name})\n\n"
                f"#### 📌 The 3 Milestone Stages:\n"
                f"- **Stage 1: Days 1–30 (Foundation & Environment Setup):** Codebase orientation, development container setup, first feature PR merged.\n"
                f"- **Stage 2: Days 31–60 (Core Feature Sprint):** Independent microservice development, mid-term evaluation by Assigned Mentor.\n"
                f"- **Stage 3: Days 61–92 (Delivery & PPO Review):** Production deployment, final presentation, and Pre-Placement Offer (PPO) evaluation.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which module would you like to explore next?\n"
                f"- [👉 3-Stage Certificate Unlock]\n"
                f"- [👉 PPO Conversion Criteria]\n"
                f"- [👉 Internship Stipend Policy]\n"
                f"- [👉 Engineering & Coding Standards]"
            ),
            "sources": ["RAGNIFY_Internship_Handbook_2026.pdf"],
            "suggested_actions": [
                "3-Stage Certificate Unlock",
                "PPO Conversion Criteria",
                "Internship Stipend Policy",
                "Engineering & Coding Standards"
            ]
        }

    # ------------------------------------------------------------------
    # L. EXACT POLICY: 3-Stage Certificate Unlock (Intern Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["certificate unlock", "intern certificate", "recommendation letter", "lor"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: 3-Stage Certificate & LOR Unlock (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Internship_Handbook_2026.pdf`\n"
                f"**Authorized Clearance:** `INTERN` ({name})\n\n"
                f"#### 📌 Certificate Unlock Criteria:\n"
                f"- **Stage 1 (Tenure Verification):** Complete 100% of the 92-day tenure period (minimum 85% task completion rate).\n"
                f"- **Stage 2 (Mentor Sign-Off):** Assigned Mentor approves code quality and sprint performance rating (>= 4.0/5.0).\n"
                f"- **Stage 3 (HR Release):** Official digitally signed Internship Certificate and Letter of Recommendation (LOR) generated with verifiable QR badge.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which area would you like to look at next?\n"
                f"- [👉 PPO Conversion Criteria]\n"
                f"- [👉 92-Day Tenure Roadmap]\n"
                f"- [👉 Internship Stipend Policy]"
            ),
            "sources": ["RAGNIFY_Internship_Handbook_2026.pdf"],
            "suggested_actions": [
                "PPO Conversion Criteria",
                "92-Day Tenure Roadmap",
                "Internship Stipend Policy"
            ]
        }

    # ------------------------------------------------------------------
    # M. EXACT POLICY: PPO Conversion Criteria (Intern Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["ppo conversion", "ppo criteria", "ppo policy", "full-time conversion", "ppo"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Pre-Placement Offer (PPO) Conversion (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Internship_Handbook_2026.pdf`\n"
                f"**Authorized Clearance:** `INTERN` ({name})\n\n"
                f"#### 📌 PPO Evaluation Benchmarks (Day 75 Review):\n"
                f"- **Task Completion Threshold:** Minimum **85% assigned task completion** with timely delivery.\n"
                f"- **Mentor Rating:** Performance rating of **4.0 or above on the 5.0 scale**.\n"
                f"- **Code Quality:** Zero critical security findings in merged pull requests, adherence to Clean Architecture.\n"
                f"- **FTE Package:** Successful candidates receive immediate full-time SDE-1 offer with competitive CTC & ESOPs.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"What would you like to examine next?\n"
                f"- [👉 92-Day Tenure Roadmap]\n"
                f"- [👉 3-Stage Certificate Unlock]\n"
                f"- [👉 Internship Stipend Policy]"
            ),
            "sources": ["RAGNIFY_Internship_Handbook_2026.pdf"],
            "suggested_actions": [
                "92-Day Tenure Roadmap",
                "3-Stage Certificate Unlock",
                "Internship Stipend Policy"
            ]
        }

    # ------------------------------------------------------------------
    # N. EXACT POLICY: Performance Appraisal & Bonus Rubric (Manager Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["performance appraisal", "appraisal rubric", "bonus rubric", "merit bonus", "rating scale"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Performance Appraisal & Bonus Rubric (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Manager_Leadership_And_Appraisal_Playbook_2026.pdf`\n"
                f"**Authorized Clearance:** `MANAGER` ({name})\n\n"
                f"#### 📌 Rating Scale & Merit Bonus Pool:\n"
                f"- **Rating 5 (Role Model - Top 10%):** 20%–22% annual merit bonus + accelerated ESOP grant.\n"
                f"- **Rating 4 (Exceeds Expectations - Top 25%):** 14%–18% annual merit bonus.\n"
                f"- **Rating 3 (Consistently Meets - Core 50%):** 8%–12% annual merit bonus.\n"
                f"- **Rating 2 (Needs Improvement):** 0% bonus; structured 30-day coaching checkpoint.\n"
                f"- **Rating 1 (Unsatisfactory):** Mandatory placement in the 45-day PIP Protocol.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which managerial guideline would you like to inspect next?\n"
                f"- [👉 45-Day PIP Protocol]\n"
                f"- [👉 Squad Discretionary Budget]\n"
                f"- [👉 Team Workload Balancing Guidelines]"
            ),
            "sources": ["RAGNIFY_Manager_Leadership_And_Appraisal_Playbook_2026.pdf"],
            "suggested_actions": [
                "45-Day PIP Protocol",
                "Squad Discretionary Budget",
                "Team Workload Balancing Guidelines"
            ]
        }

    # ------------------------------------------------------------------
    # O. EXACT POLICY: 45-Day PIP Protocol (Manager Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["pip protocol", "pip", "45-day pip", "45 day pip", "performance improvement plan"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: 45-Day Performance Improvement Plan (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Manager_Leadership_And_Appraisal_Playbook_2026.pdf`\n"
                f"**Authorized Clearance:** `MANAGER` ({name})\n\n"
                f"#### 📌 PIP Execution Protocol:\n"
                f"- **Duration:** Exactly **45 calendar days** from formal delivery.\n"
                f"- **Weekly Checkpoints:** Documented 1-on-1 coaching sessions every Friday with written action items.\n"
                f"- **Objective Goals:** Maximum of 3 measurable technical deliverables with clear acceptance criteria.\n"
                f"- **Resolution:** Successful closure returns employee to good standing; lack of improvement leads to HR transition.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which area would you like to check next?\n"
                f"- [👉 Performance Appraisal & Bonus Rubric]\n"
                f"- [👉 Squad Discretionary Budget]\n"
                f"- [👉 Team Workload Balancing Guidelines]"
            ),
            "sources": ["RAGNIFY_Manager_Leadership_And_Appraisal_Playbook_2026.pdf"],
            "suggested_actions": [
                "Performance Appraisal & Bonus Rubric",
                "Squad Discretionary Budget",
                "Team Workload Balancing Guidelines"
            ]
        }

    # ------------------------------------------------------------------
    # P. EXACT POLICY: Squad Discretionary Budget (Manager Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["squad budget", "discretionary budget", "150000", "1,50,000", "team budget"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Squad Discretionary Budget (2026)\n\n"
                f"**Source Document:** `RAGNIFY_Manager_Leadership_And_Appraisal_Playbook_2026.pdf`\n"
                f"**Authorized Clearance:** `MANAGER` ({name})\n\n"
                f"#### 📌 Budget Guidelines:\n"
                f"- **Quarterly Allocation:** **₹1,50,000 per quarter** per engineering squad.\n"
                f"- **Authorized Uses:** Team offsites, hackathons, team dinners, certification rewards, and morale events.\n"
                f"- **Approval:** Managed directly at Manager discretion with one-click portal expense receipt upload.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which module would you like to review next?\n"
                f"- [👉 Performance Appraisal & Bonus Rubric]\n"
                f"- [👉 45-Day PIP Protocol]\n"
                f"- [👉 Team Workload Balancing Guidelines]"
            ),
            "sources": ["RAGNIFY_Manager_Leadership_And_Appraisal_Playbook_2026.pdf"],
            "suggested_actions": [
                "Performance Appraisal & Bonus Rubric",
                "45-Day PIP Protocol",
                "Team Workload Balancing Guidelines"
            ]
        }

    # ------------------------------------------------------------------
    # Q. EXACT POLICY: L1–L4 Salary & ESOP Bands (HR / Admin Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["salary band", "salary bands", "l1-l4", "compensation grid", "esop bands"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: L1–L4 Compensation & ESOP Grids (2026)\n\n"
                f"**Source Document:** `RAGNIFY_HR_Compensation_Grids_And_Executive_Governance_2026.pdf`\n"
                f"**Authorized Clearance:** `{role}` ({name})\n\n"
                f"#### 📌 Engineering Compensation Grid:\n"
                f"- **L1 (Associate SDE):** ₹6,00,000 – ₹10,00,000 base | Performance bonus up to 10%.\n"
                f"- **L2 (Software Engineer):** ₹12,00,000 – ₹20,00,000 base | 2,000 ESOP units (4-yr vest, 1-yr cliff).\n"
                f"- **L3 (Senior SDE / Tech Lead):** ₹22,00,000 – ₹36,00,000 base | 5,000 ESOP units.\n"
                f"- **L4 (Principal / Staff SDE):** ₹38,00,000 – ₹55,00,000 base | 12,000 ESOP units.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which HR governance policy would you like to check next?\n"
                f"- [👉 Severance & Termination Protocol]\n"
                f"- [👉 Internship Program Governance]\n"
                f"- [👉 Annual Leave Policy]"
            ),
            "sources": ["RAGNIFY_HR_Compensation_Grids_And_Executive_Governance_2026.pdf"],
            "suggested_actions": [
                "Severance & Termination Protocol",
                "Internship Program Governance",
                "Annual Leave Policy"
            ]
        }

    # ------------------------------------------------------------------
    # R. EXACT POLICY: Severance & Termination Protocol (HR / Admin Role)
    # ------------------------------------------------------------------
    if any(k in msg_lower for k in ["severance", "termination protocol", "exit policy", "notice period"]):
        return {
            "answer": (
                f"### 📢 Official Policy Notification: Severance & Separation Protocol (2026)\n\n"
                f"**Source Document:** `RAGNIFY_HR_Compensation_Grids_And_Executive_Governance_2026.pdf`\n"
                f"**Authorized Clearance:** `{role}` ({name})\n\n"
                f"#### 📌 Separation Provisions:\n"
                f"- **Notice Period:** Standard **60 calendar days** for full-time employees, or salary in lieu of notice upon mutual agreement.\n"
                f"- **Statutory Gratuity:** Paid at 15 days of last drawn base salary per completed year of service (for tenure >= 5 years).\n"
                f"- **Leave Encashment:** Unused annual casual leave balance paid out in Full & Final Settlement (FFS) within **30 days** of exit.\n\n"
                f"#### 👨‍🏫 Teacher's Socratic Follow-Up:\n"
                f"Which module shall we explore next?\n"
                f"- [👉 L1–L4 Salary & ESOP Bands]\n"
                f"- [👉 Internship Program Governance]\n"
                f"- [👉 Annual Leave Policy]"
            ),
            "sources": ["RAGNIFY_HR_Compensation_Grids_And_Executive_Governance_2026.pdf"],
            "suggested_actions": [
                "L1–L4 Salary & ESOP Bands",
                "Internship Program Governance",
                "Annual Leave Policy"
            ]
        }
    # ------------------------------------------------------------------
    # S. BROAD INQUIRY: "policies", "what policies", "tell me about info", etc.
    # ------------------------------------------------------------------
    broad_triggers = [
        "policies", "policy", "what policies", "tell me about policies", "list of policies",
        "company policies", "what are the policies", "available policies", "all policies",
        "rules", "handbooks", "what can i read", "what can you do", "help me with policies",
        "guide me", "which policies", "info", "information", "what info", "company info",
        "show policies", "policy list", "available info", "help"
    ]
    if any(t == msg_lower or msg_lower.startswith(t) or f" {t} " in f" {msg_lower} " for t in broad_triggers):
        options_markdown = "\n".join([f"{i+1}. **[👉 {item['title']}]** — {item['desc']}" for i, item in enumerate(role_config)])
        return {
            "answer": (
                f"### 🎓 RAGNIFY Policy Guide\n\n"
                f"Hello **{name}**! I have these policies available for your **`{role}`** role. Which one would you like to read?\n\n"
                f"{options_markdown}\n\n"
                f"---\n"
                f"👉 **I have these policies available for you. Which one would you like to read? Click any option above or below:**"
            ),
            "sources": [f"RAGNIFY Official Policy Index ({role})"],
            "suggested_actions": role_action_titles
        }

    return None



def get_ai_assistant_response(
    user_message: str,
    user_role: str = "EMPLOYEE",
    user_name: str = "User",
    user_email: str = "",
    history: Optional[List[dict]] = None,
    assistant_mode: str = "AI"
) -> dict:
    """
    Unified Enterprise AI & RAG Copilot Engine with:
    1. 3-Layer RBAC & Individual Employee Privacy Guard
    2. Role-Filtered ChromaDB Vector Retrieval
    3. Role-Scoped Live PostgreSQL Database Context
    4. Multi-Turn Conversational Groq Synthesis & PDF/PPT Report Generation
    """
    message = (user_message or "").strip()
    role_upper = (user_role or "EMPLOYEE").upper()

    if not message:
        return {
            "answer": "Please enter a question or request.",
            "sources": [],
            "download_url": None,
            "file_type": None
        }

    # 1. Enforce Role Clearance & Individual Employee Privacy Guard
    allowed, rejection_msg, guard_sources = check_role_and_privacy_guard(
        message=message,
        user_role=role_upper,
        user_name=user_name,
        assistant_mode=assistant_mode
    )
    if not allowed:
        return {
            "answer": rejection_msg,
            "sources": guard_sources,
            "download_url": None,
            "file_type": None,
            "file_name": None
        }

    try:
        # 2. Retrieve RBAC-filtered document chunks from ChromaDB
        retrieved_items = search_documents_with_metadata(
            query=message,
            n_results=6,
            role=role_upper
        )

        valid_chunks = [item["text"] for item in retrieved_items]
        sources = []
        seen = set()
        for item in retrieved_items:
            fname = item.get("filename")
            if fname and fname not in seen:
                seen.add(fname)
                sources.append(fname)

        # 3. Inject Role-Scoped Live Database Context (respecting individual employee privacy)
        live_db_context = build_live_role_scoped_db_context(user_role=role_upper, user_name=user_name)

        # 4. Also check if user asks about ChromaDB / Knowledge Base document inventory
        if any(k in message.lower() for k in ["chromadb", "how many document", "indexed document", "knowledge base list", "what documents are stored"]):
            kb_summary = get_indexed_documents_summary(role=role_upper)
            kb_lines = [
                f"=== CHROMADB KNOWLEDGE BASE INVENTORY (Role: {role_upper}) ===",
                f"Total Documents in ChromaDB: {kb_summary['total_documents']} | Accessible to {role_upper}: {kb_summary['accessible_documents_count']} | Total Vector Chunks: {kb_summary['total_chunks']}"
            ]
            for d in kb_summary["documents"]:
                status_str = "ACCESSIBLE" if d["accessible"] else f"RESTRICTED ({d['access_tier']})"
                kb_lines.append(f"• {d['name']} ({d['chunks']} chunks, Tier: {d['access_tier']}, Roles: {d['allowed_roles']}) -> [{status_str}]")
            live_db_context = "\n".join(kb_lines) + "\n\n" + live_db_context

        # 5. Check if query relates to Notifications, Announcements, or Messages
        is_notif_query = any(k in message.lower() for k in [
            "notification", "notifications", "announcement", "announcements",
            "message", "messages", "alert", "alerts", "notice", "notices",
            "broadcast", "inbox", "reply", "replies", "update from hr", "update from manager"
        ])

        if is_notif_query:
            from database import SessionLocal
            import models
            db_s = SessionLocal()
            try:
                notifs = db_s.query(models.Notification).order_by(models.Notification.created_at.desc()).limit(10).all()
                if notifs:
                    notif_lines = []
                    for n in notifs:
                        # Filter private notifications so employees only see broadcasts or their own
                        t_role = (n.target_role or "ALL").upper()
                        t_name = (n.target_name or "").lower()
                        if role_upper not in ("HR", "ADMIN") and t_role not in ("ALL", role_upper) and user_name.lower() not in t_name:
                            continue
                        replies_count = db_s.query(models.Notification).filter(models.Notification.parent_id == n.notification_id).count()
                        notif_lines.append(
                            f"• [ID: {n.notification_id}] Sender: {n.sender_name} ({n.sender_role}) -> Audience: {n.target_name or n.target_role}\n"
                            f"  Title: {n.title}\n"
                            f"  Date/Time: {n.created_at.strftime('%Y-%m-%d %H:%M') if n.created_at else 'Recent'}\n"
                            f"  Message Body: {n.message}\n"
                            f"  Type: {n.notification_type} | Thread Replies: {replies_count}"
                        )
                    if notif_lines:
                        notif_context_block = "CURRENT LIVE WORKPLACE NOTIFICATIONS & ANNOUNCEMENTS:\n" + "\n\n".join(notif_lines)
                        live_db_context = notif_context_block + "\n\n" + live_db_context
                        sources.insert(0, "Enterprise Notifications Hub")
            except Exception as e:
                print(f"Error loading notifications into AI Assistant context: {e}")
            finally:
                db_s.close()

        doc_context_str = "\n\n".join(valid_chunks) if valid_chunks else "Standard RAGNIFY Role-Scoped Guidelines."
        full_context = f"{doc_context_str}\n\n{live_db_context}"

        # 6. Check for File Generation Intent (PDF or PPT)
        intent, topic = detect_generation_intent(message)

        # 6.1 Two-Way Socratic Teacher Policy Dialogue / Notification Engine
        if intent == "none":
            socratic_res = handle_socratic_policy_dialogue(
                message=message,
                user_role=role_upper,
                user_name=user_name
            )
            if socratic_res:
                return {
                    "answer": socratic_res["answer"],
                    "sources": socratic_res.get("sources", [f"RAGNIFY {role_upper} Knowledge Base"]),
                    "download_url": None,
                    "file_type": None,
                    "file_name": None,
                    "suggested_actions": socratic_res.get("suggested_actions", [])
                }

        if intent == "pptx":
            report_data = extract_report_content(topic, full_context, format_type="pptx")
            pptx_res = generate_pptx_presentation(
                title=report_data.get("title", topic.title()),
                subtitle=report_data.get("subtitle", f"Enterprise Briefing • Clearance: {role_upper}"),
                slides_data=report_data.get("slides", []),
                custom_filename=topic
            )

            slide_titles = [f"• **Slide {i+1}:** {s.get('title', 'Topic')}" for i, s in enumerate(report_data.get("slides", []))]
            summary_text = (
                f"### 📊 PowerPoint Presentation Generated!\n\n"
                f"I have compiled a professional **{len(report_data.get('slides', [])) + 1}-slide presentation** on **{report_data.get('title', topic.title())}** grounded in your authorized `{role_upper}` knowledge base.\n\n"
                f"#### **Slide Structure:**\n"
                + "\n".join(slide_titles) + "\n\n"
                f"Click the button below to download the editable PowerPoint deck (`.pptx`):"
            )

            return {
                "answer": summary_text,
                "sources": sources or ["RAGNIFY Knowledge Base"],
                "download_url": pptx_res["download_url"],
                "file_type": "pptx",
                "file_name": pptx_res["filename"],
                "suggested_actions": ["Annual Leave Policy", "Generate Policy PDF Report", "Return to Policy Menu"]
            }

        elif intent == "pdf":
            report_data = extract_report_content(topic, full_context, format_type="pdf")
            pdf_res = generate_pdf_report(
                title=report_data.get("title", topic.title()),
                overview=report_data.get("overview", "Official Policy Report"),
                sections=report_data.get("sections", []),
                custom_filename=topic
            )

            sec_titles = [f"• **{s.get('title', 'Section')}**" for s in report_data.get("sections", [])]
            summary_text = (
                f"### 📄 Official PDF Policy Report Generated!\n\n"
                f"I have prepared a formal **PDF Report** for **{report_data.get('title', topic.title())}** based on your `{role_upper}` clearance.\n\n"
                f"**Executive Summary:** {report_data.get('overview', '')}\n\n"
                f"#### **Included Sections:**\n"
                + "\n".join(sec_titles) + "\n\n"
                f"Click the download button below to save the verified `.pdf` document:"
            )

            return {
                "answer": summary_text,
                "sources": sources or ["RAGNIFY Knowledge Base"],
                "download_url": pdf_res["download_url"],
                "file_type": "pdf",
                "file_name": pdf_res["filename"],
                "suggested_actions": ["Annual Leave Policy", "Create PowerPoint Presentation", "Return to Policy Menu"]
            }

        # 7. Standard ChatGPT-Style Conversational Answer with Socratic Teacher Prompt
        answer = generate_answer(
            question=message,
            context=full_context,
            user_role=role_upper,
            user_name=user_name,
            history=history
        )

        extracted_actions = extract_action_tags(answer)
        if not extracted_actions:
            if role_upper == "INTERN":
                extracted_actions = ["Internship Stipend Policy", "92-Day Tenure Roadmap", "Intern Leave & Attendance", "3-Stage Certificate Unlock"]
            elif role_upper == "MANAGER":
                extracted_actions = ["Performance Appraisal & Bonus Rubric", "45-Day PIP Protocol", "Squad Discretionary Budget", "Annual Leave Policy"]
            elif role_upper in ("HR", "ADMIN"):
                extracted_actions = ["Annual Leave Policy", "L1–L4 Salary & ESOP Bands", "Severance & Termination Protocol", "Generate Leave Policy PDF"]
            else:
                extracted_actions = ["Annual Leave Policy", "Sick & Emergency Leave Policy", "Equipment Allowance Policy (₹5,500)", "Generate Leave Policy PDF"]

        return {
            "answer": answer,
            "sources": sources if sources else [f"RAGNIFY {role_upper} Knowledge Base"],
            "download_url": None,
            "file_type": None,
            "file_name": None,
            "suggested_actions": extracted_actions
        }

    except Exception as e:
        print(f"AI Assistant Error: {e}")
        return {
            "answer": (
                "### ⚡ RAGNIFY Enterprise AI Copilot\n\n"
                "I processed your request using our internal policy rules:\n"
                "- **Full-Time Employees (`EMPLOYEE`/`MANAGER`/`HR`/`ADMIN`):** Entitled to **18 Casual Leaves**, **12 Sick Leaves**, **₹5,500 Equipment Allowance** (within 30 days), and **₹5,00,000 Health Insurance**.\n"
                "- **Interns (`INTERN`):** Entitled to **₹30,000/month stipend**, **92-day tenure**, and official Certificate of Completion upon HR sign-off.\n"
                "- **Privacy & RBAC:** Strict individual employee privacy and role-based document governance are active."
            ),
            "sources": ["RAGNIFY Enterprise Knowledge Base"],
            "download_url": None,
            "file_type": None,
            "file_name": None,
            "suggested_actions": ["Annual Leave Policy", "Sick & Emergency Leave Policy", "Equipment Allowance Policy (₹5,500)"]
        }
