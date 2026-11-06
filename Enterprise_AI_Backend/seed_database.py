import os
import json
from datetime import datetime, date
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
import models
from utils.security import hash_password

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "HR_onboaring datasets", "datasets")
JSON_PATH = os.path.join(DATASET_DIR, "master_candidates.json")
ENTERPRISE_DATASET_SQL = os.path.join(BASE_DIR, "Enterprise_AI_Dataset", "SQL", "seed.sql")
DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "documents")
os.makedirs(DOCS_DIR, exist_ok=True)

def parse_date(val):
    if not val or str(val).strip() in ("", "None", "null"):
        return None
    try:
        return datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
    except Exception:
        return None

def seed_demo_users(db: Session):
    existing = db.query(models.User).count()
    if existing > 0:
        return
    print("[Seed] Seeding demo authentication users...")
    demo_users = [
        ("USR-001", "hr@ragnify.com", "password123", "HR", "EMP009", None),
        ("USR-002", "manager@ragnify.com", "password123", "Manager", None, "MGR001"),
        ("USR-003", "employee@ragnify.com", "password123", "Employee", "EMP001", None),
        ("USR-004", "intern@ragnify.com", "password123", "Intern", "CAND-001", None),
        ("USR-005", "admin@ragnify.com", "password123", "Admin", "EMP001", None),
        ("USR-006", "finance@ragnify.com", "password123", "Finance", "EMP004", None),
    ]
    for uid, email, pwd, role, emp_id, mgr_id in demo_users:
        user = models.User(
            user_id=uid,
            email=email,
            password=hash_password(pwd),
            role=role,
            employee_id=emp_id,
            manager_id=mgr_id
        )
        db.add(user)
    db.commit()

def seed_enterprise_data(db: Session):
    if db.query(models.Manager).count() == 0:
        print("[Seed] Seeding managers...")
        mgr1 = models.Manager(manager_id="MGR001", name="Aarav Menon", manager_name="Aarav Menon", email="aarav.menon@technova.co.in", phone="+91-98765-21011", department="Engineering", experience="12 years")
        mgr2 = models.Manager(manager_id="MGR002", name="Priya Nair", manager_name="Priya Nair", email="priya.nair@technova.co.in", phone="+91-98765-21012", department="People Operations and QA", experience="10 years")
        db.add_all([mgr1, mgr2])
        db.commit()

    if db.query(models.Employee).count() == 0:
        print("[Seed] Seeding employees from Enterprise Dataset...")
        emp_records = [
            ("EMP001", "Rohan Sharma", "rohan.sharma@technova.co.in", "+91-98765-22101", "Male", "1998-03-14", "2022-07-11", "AI Team", "AI Engineer", "MGR001", "4 years", "Python; LangChain; RAG; Prompt Engineering; Vector Databases", 1150000, "Active"),
            ("EMP002", "Ananya Iyer", "ananya.iyer@technova.co.in", "+91-98765-22102", "Female", "1997-11-06", "2021-09-20", "AI Team", "Machine Learning Engineer", "MGR001", "5 years", "PyTorch; NLP; Model Evaluation; MLOps; FastAPI", 1250000, "Active"),
            ("EMP003", "Vikram Rao", "vikram.rao@technova.co.in", "+91-98765-22103", "Male", "1996-05-29", "2020-02-17", "Backend", "Senior Backend Developer", "MGR001", "6 years", "Node.js; PostgreSQL; REST APIs; Redis; System Design", 1320000, "Active"),
            ("EMP004", "Meera Krishnan", "meera.krishnan@technova.co.in", "+91-98765-22104", "Female", "1999-01-21", "2023-01-09", "Backend", "Backend Developer", "MGR001", "3 years", "Java; Spring Boot; SQL; Docker; API Testing", 930000, "Active"),
            ("EMP005", "Arjun Patel", "arjun.patel@technova.co.in", "+91-98765-22105", "Male", "1998-08-10", "2022-04-04", "Frontend", "Frontend Developer", "MGR001", "4 years", "React; TypeScript; Tailwind CSS; Redux; Accessibility", 980000, "Active"),
            ("EMP006", "Sneha Kulkarni", "sneha.kulkarni@technova.co.in", "+91-98765-22106", "Female", "1997-02-19", "2021-06-14", "Frontend", "UI Engineer", "MGR001", "5 years", "React; Figma; Component Design; HTML; CSS", 1040000, "Active"),
            ("EMP007", "Karthik Reddy", "karthik.reddy@technova.co.in", "+91-98765-22107", "Male", "1995-12-03", "2019-10-07", "QA", "QA Lead", "MGR002", "7 years", "Automation Testing; Cypress; Selenium; Test Strategy; Jira", 1180000, "Active"),
            ("EMP008", "Nisha Gupta", "nisha.gupta@technova.co.in", "+91-98765-22108", "Female", "2000-04-25", "2023-08-16", "QA", "QA Engineer", "MGR002", "2 years", "Manual Testing; API Testing; Regression; Postman; SQL", 720000, "Active"),
            ("EMP009", "Farhan Khan", "farhan.khan@technova.co.in", "+91-98765-22109", "Male", "1996-09-12", "2020-11-23", "HR", "HR Executive", "MGR002", "5 years", "Recruitment; Payroll; Employee Engagement; Policy Drafting; HRMS", 850000, "Active"),
            ("EMP010", "Divya Singh", "divya.singh@technova.co.in", "+91-98765-22110", "Female", "1999-07-18", "2022-12-01", "HR", "Operations Coordinator", "MGR002", "3 years", "Vendor Coordination; Documentation; Onboarding; Excel; Compliance", 780000, "Active")
        ]
        for e in emp_records:
            emp = models.Employee(
                employee_id=e[0], full_name=e[1], email=e[2], phone_number=e[3], gender=e[4],
                date_of_birth=parse_date(e[5]), joining_date=parse_date(e[6]), department=e[7],
                designation=e[8], manager_id=e[9], experience=e[10], skills=e[11],
                salary_demo=e[12], employment_status=e[13]
            )
            db.add(emp)
        db.commit()

    if db.query(models.Meeting).count() == 0:
        print("[Seed] Seeding meetings from Enterprise Dataset...")
        meetings_data = [
            ("MTG001", "Sprint Planning for Enterprise AI Workspace", "2026-01-08", "60 minutes", "Aarav Menon", "Rohan Sharma; Ananya Iyer; Vikram Rao; Arjun Patel; Karthik Reddy", "Finalize sprint scope and assign ownership for authentication, dashboards, and RAG discovery.", "Sprint 1 will prioritize login, employee dashboard shell, authentication API, and RAG proof of concept.", "Rohan to prepare vector store plan; Vikram to publish auth API contract; Arjun to start login page."),
            ("MTG002", "AI Assistant Architecture Review", "2026-01-24", "75 minutes", "Aarav Menon", "Rohan Sharma; Ananya Iyer; Vikram Rao; Meera Krishnan", "Review AI assistant service boundary, document retrieval, security, and latency targets.", "Adopt FastAPI service for assistant orchestration and keep document access filtered by role metadata.", "Ananya to define evaluation set; Meera to add API logging; Rohan to configure ChromaDB collections."),
            ("MTG003", "Dashboard Progress Sync", "2026-02-07", "45 minutes", "Aarav Menon", "Arjun Patel; Sneha Kulkarni; Vikram Rao; Divya Singh", "Check employee and manager dashboard progress, data contracts, and blocker list.", "Manager dashboard will expose completion rate, overdue tasks, and department performance from the same task table.", "Sneha to finish metric cards; Vikram to add task summary endpoint; Divya to validate label wording."),
            ("MTG004", "QA Test Strategy Review", "2026-02-21", "60 minutes", "Priya Nair", "Karthik Reddy; Nisha Gupta; Meera Krishnan; Arjun Patel", "Define QA approach for authentication, dashboards, document retrieval, and regression cycles.", "Cypress will cover core UI workflows and Postman collections will validate API contracts.", "Karthik to draft test plan; Nisha to create regression checklist; Meera to share test credentials."),
            ("MTG005", "HR Policy Digitization Workshop", "2026-03-05", "50 minutes", "Priya Nair", "Farhan Khan; Divya Singh; Rohan Sharma; Ananya Iyer", "Prepare HR and company policy documents for RAG ingestion and employee self-service.", "Policies will be chunked by section and tagged by policy type, effective date, and audience.", "Farhan to finalize leave policy; Divya to standardize document headers; Ananya to test retrieval quality."),
            ("MTG006", "Client Feedback Review for Project Alpha", "2026-03-19", "60 minutes", "Aarav Menon", "Rohan Sharma; Ananya Iyer; Arjun Patel; Sneha Kulkarni; Karthik Reddy", "Discuss client feedback on dashboard navigation, assistant response tone, and export requirements.", "Team will add clearer status filters, export-ready dashboard data, and concise assistant citations.", "Sneha to update filter design; Rohan to tune assistant prompt; Karthik to add acceptance scenarios."),
            ("MTG007", "RAG Module Deep Dive", "2026-04-02", "90 minutes", "Aarav Menon", "Rohan Sharma; Ananya Iyer; Vikram Rao; Nisha Gupta", "Validate ingestion pipeline, embedding metadata, retrieval relevance, and fallback behavior.", "Use document version metadata to prefer latest approved files while preserving older versions for audit.", "Ananya to add version-aware retrieval tests; Vikram to expose document list endpoint; Nisha to run query set."),
            ("MTG008", "Deployment Readiness Check", "2026-04-23", "60 minutes", "Aarav Menon", "Vikram Rao; Meera Krishnan; Karthik Reddy; Divya Singh", "Review Docker setup, environment variables, rollback plan, and release documentation.", "Release candidate will deploy to staging after security policy review and QA sign-off.", "Meera to update compose file; Karthik to publish sign-off report; Divya to prepare release checklist."),
            ("MTG009", "Monthly Performance and Workload Review", "2026-05-14", "55 minutes", "Priya Nair", "Farhan Khan; Divya Singh; Karthik Reddy; Nisha Gupta; Sneha Kulkarni", "Review employee workload balance, pending tasks, and support needs.", "Tasks are evenly distributed, but QA requires two focused regression windows before final demo.", "Farhan to update workload tracker; Nisha to flag high-risk test cases; Sneha to close dashboard UI issues."),
            ("MTG010", "Final Demo Preparation", "2026-06-10", "75 minutes", "Aarav Menon", "Rohan Sharma; Ananya Iyer; Vikram Rao; Arjun Patel; Sneha Kulkarni; Karthik Reddy; Farhan Khan", "Prepare final year project demo flow, data story, known limitations, and presentation sequence.", "Demo will show login, dashboards, task workflow, document search, AI assistant, and SQL-backed analytics.", "Rohan to prepare AI demo prompts; Arjun to verify UI flows; Karthik to perform final smoke test.")
        ]
        for m in meetings_data:
            mtg = models.Meeting(
                meeting_id=m[0], meeting_title=m[1], meeting_date=parse_date(m[2]),
                duration=m[3], organizer=m[4], participants=m[5], agenda=m[6],
                decisions=m[7], action_items=m[8]
            )
            db.add(mtg)
        db.commit()

    if db.query(models.Task).count() == 0:
        print("[Seed] Seeding tasks from Enterprise Dataset...")
        tasks_data = [
            ("TSK001", "Build Login Page - Sprint 1", "Create responsive login, validation, and error states for the Enterprise AI Workspace portal.", "EMP005", "MGR001", "High", "Completed", "2026-01-06", "2026-01-07", "2026-01-12", "2026-01-12", "8", "6"),
            ("TSK002", "Develop Manager Dashboard - Sprint 1", "Implement manager metrics, team task filters, and drill-down panels.", "EMP006", "MGR001", "Medium", "Completed", "2026-01-08", "2026-01-10", "2026-01-16", "2026-01-15", "11", "10"),
            ("TSK003", "Employee Dashboard - Sprint 1", "Build employee view for tasks, meetings, documents, and productivity cards.", "EMP005", "MGR001", "Medium", "Completed", "2026-01-10", "2026-01-13", "2026-01-20", "2026-01-19", "14", "14"),
            ("TSK004", "Authentication API - Sprint 1", "Create JWT based login, refresh token, password policy checks, and audit logging.", "EMP003", "MGR001", "Low", "Completed", "2026-01-12", "2026-01-13", "2026-01-21", "2026-01-20", "17", "18"),
            ("TSK005", "AI Assistant Integration - Sprint 1", "Connect workspace chat UI to the internal AI assistant service with secure context passing.", "EMP001", "MGR001", "High", "Completed", "2026-01-14", "2026-01-16", "2026-01-25", "2026-01-25", "20", "22"),
            ("TSK006", "RAG Integration - Sprint 1", "Build retrieval pipeline for policy documents, meeting transcripts, and project requirements.", "EMP002", "MGR001", "High", "Completed", "2026-01-16", "2026-01-19", "2026-01-29", "2026-01-28", "23", "21"),
            ("TSK007", "ChromaDB Setup - Sprint 1", "Configure vector collection schema, metadata filters, and local development seeding.", "EMP001", "MGR001", "Medium", "Completed", "2026-01-18", "2026-01-19", "2026-01-30", "2026-01-29", "26", "25"),
            ("TSK008", "Database Optimization - Sprint 1", "Review slow dashboard queries and add indexes for task and employee analytics.", "EMP003", "MGR001", "Medium", "Completed", "2026-01-20", "2026-01-22", "2026-02-03", "2026-02-02", "8", "8"),
            ("TSK009", "Bug Fixing - Sprint 1", "Fix defects from sprint QA, including form validation and API response handling.", "EMP004", "MGR001", "Low", "Completed", "2026-01-22", "2026-01-25", "2026-01-30", "2026-01-30", "11", "12"),
            ("TSK010", "Unit Testing - Sprint 1", "Add unit tests for services, utility functions, and critical frontend components.", "EMP008", "MGR002", "High", "Completed", "2026-01-24", "2026-01-25", "2026-01-31", "2026-01-30", "14", "16"),
            ("TSK037", "Build Login Page - Sprint 4", "Create responsive login, validation, and error states for the Enterprise AI Workspace portal.", "EMP007", "MGR002", "Medium", "In Progress", "2026-03-19", "2026-03-20", "2026-03-29", None, "11", "4"),
            ("TSK038", "Develop Manager Dashboard - Sprint 4", "Implement manager metrics, team task filters, and drill-down panels.", "EMP006", "MGR001", "Medium", "In Progress", "2026-03-21", "2026-03-23", "2026-04-02", None, "14", "7"),
            ("TSK052", "Authentication API - Sprint 6", "Create JWT based login, refresh token, password policy checks, and audit logging.", "EMP007", "MGR002", "Medium", "Pending", "2026-04-18", "2026-04-19", "2026-06-25", None, "14", "0"),
            ("TSK053", "AI Assistant Integration - Sprint 6", "Connect workspace chat UI to the internal AI assistant service with secure context passing.", "EMP007", "MGR002", "Medium", "Pending", "2026-04-20", "2026-04-22", "2026-05-01", None, "17", "0")
        ]
        for t in tasks_data:
            task = models.Task(
                task_id=t[0], task_title=t[1], description=t[2], assigned_employee_id=t[3],
                assigned_manager_id=t[4], priority=t[5], status=t[6], created_date=parse_date(t[7]),
                start_date=parse_date(t[8]), deadline=parse_date(t[9]),
                completion_date=parse_date(t[10]) if t[10] else None,
                estimated_hours=t[11], actual_hours=t[12]
            )
            db.add(task)
        db.commit()

def seed_candidate_dataset(db: Session):
    if not os.path.exists(JSON_PATH):
        print(f"[Seed] Candidates JSON not found at {JSON_PATH}")
        return

    print("[Seed] Loading HR Onboarding master_candidates.json...")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. HR Staff
    for hr in data.get("hr_staff", []):
        if not db.query(models.HRStaff).filter(models.HRStaff.hr_id == hr["hr_id"]).first():
            db.add(models.HRStaff(hr_id=hr["hr_id"], hr_name=hr["hr_name"], hr_email=hr["hr_email"]))
    db.commit()

    # 2. Managers
    for m in data.get("managers", []):
        if not db.query(models.Manager).filter(models.Manager.manager_id == m["manager_id"]).first():
            db.add(models.Manager(
                manager_id=m["manager_id"],
                name=m["manager_name"],
                manager_name=m["manager_name"],
                department=m.get("department", "Engineering")
            ))
    db.commit()

    # 3. Candidates
    candidates = data.get("candidates", [])[:15]
    for c in candidates:
        cid = c["candidate_id"]
        if db.query(models.CandidateProfile).filter(models.CandidateProfile.candidate_id == cid).first():
            continue
        p = c["personal_information"]
        cp = models.CandidateProfile(
            candidate_id=cid,
            full_name=p["full_name"],
            gender=p["gender"],
            date_of_birth=parse_date(p["date_of_birth"]) or date(2000, 1, 1),
            nationality=p.get("nationality", "Indian"),
            marital_status=p.get("marital_status", "Single"),
            blood_group=p.get("blood_group", "O+"),
            profile_photo_filename=p.get("profile_photo_filename", f"{cid}_photo.jpg"),
            candidate_type=p.get("candidate_type", "Employee"),
            data_classification=p.get("data_classification", "SYNTHETIC_DEMO")
        )
        db.add(cp)
        db.commit()

        # Contact Details
        ci = c.get("contact_information", {})
        if ci:
            db.add(models.ContactDetails(
                contact_id=ci.get("contact_id", f"CON-{cid}"),
                candidate_id=cid,
                personal_email=ci.get("personal_email", f"{cid.lower()}@example.com"),
                official_email=ci.get("official_email", f"{cid.lower()}@ragnify.com"),
                mobile_number=ci.get("mobile_number", "+91-98000-00000"),
                alternate_phone=ci.get("alternate_phone")
            ))

        # Addresses
        addr = c.get("address_information", {})
        for atype in ["current", "permanent"]:
            if atype in addr:
                ainfo = addr[atype]
                db.add(models.Address(
                    address_id=f"ADR-{cid}-{atype[:4].upper()}",
                    candidate_id=cid,
                    address_type=atype.capitalize(),
                    address_line=ainfo.get("address_line", "Demo Street"),
                    city=ainfo.get("city", "Mumbai"),
                    state=ainfo.get("state", "Maharashtra"),
                    country=ainfo.get("country", "India"),
                    pin_code=str(ainfo.get("pin_code", "400001"))
                ))

        # Emergency Contact
        emc = c.get("emergency_contact", {})
        if emc:
            db.add(models.EmergencyContact(
                emergency_contact_id=emc.get("emergency_contact_id", f"EMC-{cid}"),
                candidate_id=cid,
                contact_name=emc.get("contact_name", "Family Contact"),
                relationship=emc.get("relationship", "Parent"),
                phone=emc.get("phone", "+91-98000-00001"),
                email=emc.get("email"),
                address=emc.get("address", "Demo Address")
            ))

        # Education
        edu_list = c.get("education", [])
        for idx, edu in enumerate(edu_list):
            db.add(models.Education(
                education_id=edu.get("education_id", f"EDU-{cid}-{idx+1}"),
                candidate_id=cid,
                level=edu.get("level", "UG"),
                qualification=edu.get("qualification", "B.Tech"),
                specialization=edu.get("specialization", "Computer Science"),
                institution=edu.get("institution", "Demo Institute"),
                board_or_university=edu.get("board_or_university", "Demo University"),
                year_of_passing=int(edu.get("year_of_passing") or 2024),
                score_type=edu.get("score_type", "Percentage"),
                score_value=float(edu.get("score_value") or 85.0),
                education_status=edu.get("education_status", "Completed"),
                is_highest_qualification=bool(edu.get("is_highest_qualification", True)),
                document_filename=edu.get("document_filename", f"{cid}_Degree.pdf"),
                verification_status=edu.get("verification_status", "Verified")
            ))

        # Employment details
        emp_det = c.get("employment_or_internship", {})
        if emp_det:
            mgr_id = emp_det.get("reporting_manager_id", "MGR001")
            hr_id = emp_det.get("hr_coordinator_id", "HR-001")
            db.add(models.EmploymentDetails(
                employment_id=emp_det.get("employment_id", f"EMP-DET-{cid}"),
                candidate_id=cid,
                candidate_type=p.get("candidate_type", "Employee"),
                job_title=emp_det.get("job_title", "Software Engineer"),
                department=emp_det.get("department", "Engineering"),
                reporting_manager_id=mgr_id,
                reporting_manager_name=emp_det.get("reporting_manager_name", "Vikram Joshi"),
                hr_coordinator_id=hr_id,
                hr_coordinator_name=emp_det.get("hr_coordinator_name", "Meera Kulkarni"),
                employment_type=emp_det.get("employment_type", "Full-time"),
                work_location=emp_det.get("work_location", "Bangalore"),
                work_mode=emp_det.get("work_mode", "Hybrid"),
                joining_date=parse_date(emp_det.get("joining_date")) or date(2025, 1, 15),
                probation_months=emp_det.get("probation_months", 3),
                annual_ctc_inr=float(emp_det.get("annual_ctc_inr") or 1200000.0),
                monthly_stipend_inr=float(emp_det.get("monthly_stipend_inr") or 35000.0)
            ))

        # Internship Tenure
        it = c.get("internship_tenure")
        if it or p.get("candidate_type") == "Intern":
            it = it or {}
            db.add(models.InternshipTenure(
                tenure_id=it.get("tenure_id", f"TEN-{cid}"),
                candidate_id=cid,
                internship_start_date=parse_date(it.get("internship_start_date")) or date(2025, 1, 1),
                internship_end_date=parse_date(it.get("internship_end_date")) or date(2025, 6, 30),
                duration_months=int(it.get("duration_months") or 6),
                objectives=it.get("objectives", "Enterprise software development and AI engineering"),
                assigned_department=it.get("assigned_department", "Engineering"),
                mentor_name=it.get("mentor_name", "Aarav Menon")
            ))

        # Working Hours
        wh = c.get("working_hours", {})
        db.add(models.WorkingHours(
            working_hours_id=wh.get("working_hours_id", f"WH-{cid}"),
            candidate_id=cid,
            start_time=wh.get("start_time", "09:30"),
            end_time=wh.get("end_time", "18:30"),
            hours_per_day=float(wh.get("hours_per_day") or 8.5),
            working_days=wh.get("working_days", "Monday to Friday"),
            shift=wh.get("shift", "General")
        ))

        # Offer Letter
        ol = c.get("offer_letters", {})
        if ol:
            db.add(models.OfferLetter(
                offer_id=ol.get("offer_id", f"OFR-{cid}"),
                candidate_id=cid,
                offer_type=ol.get("offer_type", "Standard"),
                offer_letter_status=ol.get("offer_letter_status", "ACCEPTED"),
                offer_letter_filename=ol.get("offer_letter_filename", f"{cid}_Offer_Letter.pdf"),
                offer_date=parse_date(ol.get("offer_date")) or date(2024, 12, 1),
                valid_until=parse_date(ol.get("valid_until")) or date(2025, 12, 31),
                position=ol.get("position", "Software Engineer"),
                department=ol.get("department", "Engineering"),
                reporting_manager_name=ol.get("reporting_manager_name", "Vikram Joshi"),
                joining_date=parse_date(ol.get("joining_date")) or date(2025, 1, 15),
                acceptance_status=ol.get("acceptance_status", "ACCEPTED"),
                acceptance_date=parse_date(ol.get("acceptance_date")) or date(2024, 12, 10),
                appointment_letter_status=ol.get("appointment_letter_status", "ISSUED")
            ))

        # HR Verification
        hrv = c.get("hr_verification", {})
        if hrv:
            db.add(models.HRVerification(
                verification_id=hrv.get("verification_id", f"HRV-{cid}"),
                candidate_id=cid,
                hr_verification_status=hrv.get("hr_verification_status", "Verified"),
                manager_verification_status=hrv.get("manager_verification_status", "Verified"),
                document_verification_status=hrv.get("document_verification_status", "Complete"),
                background_verification_status=hrv.get("background_verification_status", "Passed"),
                overall_onboarding_status=hrv.get("overall_onboarding_status", "Completed"),
                missing_documents=hrv.get("missing_documents", ""),
                hr_remarks=hrv.get("hr_remarks", "All verification checks passed."),
                manager_remarks=hrv.get("manager_remarks", "Approved by hiring manager."),
                hr_verified_date=parse_date(hrv.get("hr_verified_date")) or date(2025, 1, 10),
                manager_verified_date=parse_date(hrv.get("manager_verified_date")) or date(2025, 1, 12),
                last_updated=date.today()
            ))

        # Documents
        for idx, d in enumerate(c.get("documents", [])):
            fn = d.get("filename", f"{cid}_Document.pdf")
            fmt = "pdf"
            if "." in fn:
                fmt = fn.split(".")[-1].lower()
            db.add(models.Document(
                document_id=d.get("document_id", f"DOC-{cid}-{idx+1}"),
                candidate_id=cid,
                document_type=d.get("document_type", "Resume"),
                filename=fn,
                file_format=fmt,
                document_status=d.get("document_status", "VERIFIED"),
                uploaded_date=parse_date(d.get("uploaded_date")) or date(2025, 1, 5),
                verified_by=d.get("verified_by", "HR-001"),
                verification_date=parse_date(d.get("verification_date")) or date(2025, 1, 10),
                remarks=d.get("remarks", "Verified document.")
            ))

        db.commit()

    print("[Seed] Candidates loaded successfully!")

def seed_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_users(db)
        seed_enterprise_data(db)
        seed_candidate_dataset(db)
        print("[Seed] Full database initialization complete.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_all()
