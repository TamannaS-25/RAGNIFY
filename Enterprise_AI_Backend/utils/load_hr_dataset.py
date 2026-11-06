import os
import json
import shutil
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

from database import engine

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = os.path.join(BASE_DIR, "HR_onboaring datasets", "datasets")
SCHEMA_SQL_PATH = os.path.join(DATASET_DIR, "schema.sql")
JSON_PATH = os.path.join(DATASET_DIR, "master_candidates.json")
DOCS_SRC_DIR = os.path.join(DATASET_DIR, "RAGNIFY_GENERATED_DOCUMENTS")
BACKEND_DOCS_DEST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "documents")

def clean_date(val):
    if not val or str(val).strip() == "" or str(val).strip().lower() == "none":
        return None
    return str(val).strip()

def clean_str(val, default=""):
    if val is None:
        return default
    return str(val).strip()

def clean_num(val, default=None):
    if val is None or str(val).strip() == "":
        return default
    try:
        return float(val)
    except:
        return default

def widen_columns(conn):
    alter_cmds = [
        "ALTER TABLE hr_staff ALTER COLUMN hr_id TYPE VARCHAR(50);",
        "ALTER TABLE managers ALTER COLUMN manager_id TYPE VARCHAR(50);",
        "ALTER TABLE managers ADD COLUMN IF NOT EXISTS manager_name VARCHAR(100);",
        "ALTER TABLE managers ADD COLUMN IF NOT EXISTS name VARCHAR(100);",
        "ALTER TABLE candidate_profile ALTER COLUMN candidate_id TYPE VARCHAR(50);",
        "ALTER TABLE addresses ALTER COLUMN address_id TYPE VARCHAR(50);",
        "ALTER TABLE contact_details ALTER COLUMN contact_id TYPE VARCHAR(50);",
        "ALTER TABLE emergency_contacts ALTER COLUMN emergency_contact_id TYPE VARCHAR(50);",
        "ALTER TABLE education ALTER COLUMN education_id TYPE VARCHAR(50);",
        "ALTER TABLE employment_details ALTER COLUMN employment_id TYPE VARCHAR(50);",
        "ALTER TABLE documents ALTER COLUMN document_id TYPE VARCHAR(120);",
        "ALTER TABLE documents ALTER COLUMN verified_by TYPE VARCHAR(50);",
        "ALTER TABLE documents ALTER COLUMN document_status TYPE VARCHAR(60);",
        "ALTER TABLE offer_letters ALTER COLUMN offer_id TYPE VARCHAR(50);",
        "ALTER TABLE offer_letters ALTER COLUMN offer_type TYPE VARCHAR(60);",
        "ALTER TABLE offer_letters ALTER COLUMN offer_letter_status TYPE VARCHAR(60);",
        "ALTER TABLE offer_letters ALTER COLUMN appointment_letter_status TYPE VARCHAR(60);",
        "ALTER TABLE onboarding_checklist ALTER COLUMN checklist_id TYPE VARCHAR(50);",
        "ALTER TABLE onboarding_checklist ALTER COLUMN status TYPE VARCHAR(60);",
        "ALTER TABLE hr_verification ALTER COLUMN verification_id TYPE VARCHAR(50);",
        "ALTER TABLE bank_payroll ALTER COLUMN bank_id TYPE VARCHAR(50);",
        "ALTER TABLE identity_verification ALTER COLUMN identity_id TYPE VARCHAR(50);",
        "ALTER TABLE internship_tenure ALTER COLUMN tenure_id TYPE VARCHAR(50);",
        "ALTER TABLE working_hours ALTER COLUMN working_hours_id TYPE VARCHAR(50);",
        "ALTER TABLE consents ALTER COLUMN consent_id TYPE VARCHAR(50);",
        "ALTER TABLE system_accounts ALTER COLUMN system_account_id TYPE VARCHAR(50);"
    ]
    for cmd in alter_cmds:
        try:
            conn.execute(text(cmd))
            conn.commit()
        except Exception:
            conn.rollback()

def setup_database_and_load():
    print("Connecting to PostgreSQL Task Management database...")
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        print(f"Connection test result: {res}")

        print("Executing schema.sql DDL...")
        with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()

        statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()

        print("Widening ID and status columns for high safety...")
        widen_columns(conn)

        print("Loading master_candidates.json...")
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Ingest HR Staff
        hr_staff = data.get("hr_staff", [])
        for hr in hr_staff:
            conn.execute(text("""
                INSERT INTO hr_staff (hr_id, hr_name, hr_email)
                VALUES (:hr_id, :hr_name, :hr_email)
                ON CONFLICT (hr_id) DO UPDATE SET
                    hr_name = EXCLUDED.hr_name,
                    hr_email = EXCLUDED.hr_email;
            """), hr)
        conn.commit()
        print(f"Ingested {len(hr_staff)} HR Staff members.")

        # 2. Ingest Managers
        mgrs = data.get("managers", [])
        for m in mgrs:
            conn.execute(text("""
                INSERT INTO managers (manager_id, name, manager_name, department)
                VALUES (:manager_id, :manager_name, :manager_name, :department)
                ON CONFLICT (manager_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    manager_name = EXCLUDED.manager_name,
                    department = EXCLUDED.department;
            """), m)
        conn.commit()
        print(f"Ingested {len(mgrs)} Managers.")

        # 3. Ingest Candidates and all related tables
        candidates = data.get("candidates", [])
        print(f"Ingesting {len(candidates)} Candidate records...")

        for c in candidates:
            cid = c["candidate_id"]
            p = c["personal_information"]
            conn.execute(text("""
                INSERT INTO candidate_profile (
                    candidate_id, full_name, gender, date_of_birth, nationality,
                    marital_status, blood_group, profile_photo_filename, candidate_type, data_classification
                ) VALUES (
                    :cid, :full_name, :gender, :date_of_birth, :nationality,
                    :marital_status, :blood_group, :profile_photo_filename, :candidate_type, :data_classification
                ) ON CONFLICT (candidate_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    candidate_type = EXCLUDED.candidate_type;
            """), {
                "cid": cid,
                "full_name": clean_str(p["full_name"]),
                "gender": clean_str(p["gender"]),
                "date_of_birth": clean_date(p["date_of_birth"]),
                "nationality": clean_str(p["nationality"], "Indian"),
                "marital_status": clean_str(p["marital_status"], "Single"),
                "blood_group": clean_str(p["blood_group"], "O+"),
                "profile_photo_filename": clean_str(p["profile_photo_filename"]),
                "candidate_type": clean_str(p["candidate_type"], "Employee"),
                "data_classification": clean_str(p.get("data_classification"), "SYNTHETIC_DEMO")
            })

            # Contact Information
            ci = c.get("contact_information", {})
            if ci:
                conn.execute(text("""
                    INSERT INTO contact_details (
                        contact_id, candidate_id, personal_email, official_email, mobile_number, alternate_phone
                    ) VALUES (
                        :contact_id, :candidate_id, :personal_email, :official_email, :mobile_number, :alternate_phone
                    ) ON CONFLICT (candidate_id) DO UPDATE SET
                        personal_email = EXCLUDED.personal_email,
                        official_email = EXCLUDED.official_email,
                        mobile_number = EXCLUDED.mobile_number;
                """), {
                    "contact_id": clean_str(ci.get("contact_id"), f"CON-{cid}"),
                    "candidate_id": cid,
                    "personal_email": clean_str(ci.get("personal_email")),
                    "official_email": clean_str(ci.get("official_email")),
                    "mobile_number": clean_str(ci.get("mobile_number")),
                    "alternate_phone": clean_str(ci.get("alternate_phone"))
                })

            # Addresses
            addr = c.get("address_information", {})
            for atype in ["current", "permanent"]:
                if atype in addr:
                    ainfo = addr[atype]
                    conn.execute(text("""
                        INSERT INTO addresses (
                            address_id, candidate_id, address_type, address_line, city, state, country, pin_code
                        ) VALUES (
                            :address_id, :candidate_id, :address_type, :address_line, :city, :state, :country, :pin_code
                        ) ON CONFLICT (address_id) DO UPDATE SET
                            address_line = EXCLUDED.address_line,
                            city = EXCLUDED.city;
                    """), {
                        "address_id": f"ADR-{cid}-{atype[:4].upper()}",
                        "candidate_id": cid,
                        "address_type": atype.capitalize(),
                        "address_line": clean_str(ainfo.get("address_line")),
                        "city": clean_str(ainfo.get("city")),
                        "state": clean_str(ainfo.get("state")),
                        "country": clean_str(ainfo.get("country"), "India"),
                        "pin_code": clean_str(ainfo.get("pin_code"), "000000")
                    })

            # Emergency Contact
            emc = c.get("emergency_contact", {})
            if emc:
                conn.execute(text("""
                    INSERT INTO emergency_contacts (
                        emergency_contact_id, candidate_id, contact_name, relationship, phone, email, address
                    ) VALUES (
                        :emergency_contact_id, :candidate_id, :contact_name, :relationship, :phone, :email, :address
                    ) ON CONFLICT (emergency_contact_id) DO UPDATE SET
                        contact_name = EXCLUDED.contact_name,
                        relationship = EXCLUDED.relationship,
                        phone = EXCLUDED.phone;
                """), {
                    "emergency_contact_id": clean_str(emc.get("emergency_contact_id"), f"EMC-{cid}"),
                    "candidate_id": cid,
                    "contact_name": clean_str(emc.get("contact_name")),
                    "relationship": clean_str(emc.get("relationship")),
                    "phone": clean_str(emc.get("phone")),
                    "email": clean_str(emc.get("email")),
                    "address": clean_str(emc.get("address"))
                })

            # Education records
            edu_list = c.get("education", [])
            for idx, edu in enumerate(edu_list):
                conn.execute(text("""
                    INSERT INTO education (
                        education_id, candidate_id, level, qualification, specialization,
                        institution, board_or_university, year_of_passing, score_type,
                        score_value, education_status, is_highest_qualification,
                        document_filename, verification_status
                    ) VALUES (
                        :education_id, :candidate_id, :level, :qualification, :specialization,
                        :institution, :board_or_university, :year_of_passing, :score_type,
                        :score_value, :education_status, :is_highest_qualification,
                        :document_filename, :verification_status
                    ) ON CONFLICT (education_id) DO UPDATE SET
                        qualification = EXCLUDED.qualification,
                        score_value = EXCLUDED.score_value;
                """), {
                    "education_id": clean_str(edu.get("education_id"), f"EDU-{cid}-{idx+1}"),
                    "candidate_id": cid,
                    "level": clean_str(edu.get("level"), "UG"),
                    "qualification": clean_str(edu.get("qualification")),
                    "specialization": clean_str(edu.get("specialization")),
                    "institution": clean_str(edu.get("institution")),
                    "board_or_university": clean_str(edu.get("board_or_university")),
                    "year_of_passing": int(edu.get("year_of_passing") or 2024),
                    "score_type": clean_str(edu.get("score_type"), "Percentage"),
                    "score_value": clean_num(edu.get("score_value"), 0.0),
                    "education_status": clean_str(edu.get("education_status"), "Completed"),
                    "is_highest_qualification": str(edu.get("is_highest_qualification")).lower() == "true",
                    "document_filename": clean_str(edu.get("document_filename")),
                    "verification_status": clean_str(edu.get("verification_status"), "Verified")
                })

            # Employment / Internship Details
            emp = c.get("employment_information") or c.get("employment_details") or {}
            if emp:
                conn.execute(text("""
                    INSERT INTO employment_details (
                        employment_id, candidate_id, candidate_type, job_title, department,
                        reporting_manager_id, reporting_manager_name, hr_coordinator_id,
                        hr_coordinator_name, employment_type, work_location, work_mode,
                        joining_date, probation_months, probation_end_date,
                        previous_experience_years, previous_employer, annual_ctc_inr, monthly_stipend_inr
                    ) VALUES (
                        :employment_id, :candidate_id, :candidate_type, :job_title, :department,
                        :reporting_manager_id, :reporting_manager_name, :hr_coordinator_id,
                        :hr_coordinator_name, :employment_type, :work_location, :work_mode,
                        :joining_date, :probation_months, :probation_end_date,
                        :previous_experience_years, :previous_employer, :annual_ctc_inr, :monthly_stipend_inr
                    ) ON CONFLICT (candidate_id) DO UPDATE SET
                        job_title = EXCLUDED.job_title,
                        department = EXCLUDED.department,
                        annual_ctc_inr = EXCLUDED.annual_ctc_inr;
                """), {
                    "employment_id": clean_str(emp.get("employment_id"), f"EMP-DET-{cid}"),
                    "candidate_id": cid,
                    "candidate_type": clean_str(p["candidate_type"], "Employee"),
                    "job_title": clean_str(emp.get("job_title")),
                    "department": clean_str(emp.get("department")),
                    "reporting_manager_id": clean_str(emp.get("reporting_manager_id"), "MGR-001"),
                    "reporting_manager_name": clean_str(emp.get("reporting_manager_name")),
                    "hr_coordinator_id": clean_str(emp.get("hr_coordinator_id"), "HR-001"),
                    "hr_coordinator_name": clean_str(emp.get("hr_coordinator_name")),
                    "employment_type": clean_str(emp.get("employment_type"), "Full-Time"),
                    "work_location": clean_str(emp.get("work_location"), "Bangalore"),
                    "work_mode": clean_str(emp.get("work_mode"), "Hybrid"),
                    "joining_date": clean_date(emp.get("joining_date")) or "2026-10-15",
                    "probation_months": clean_num(emp.get("probation_months")),
                    "probation_end_date": clean_date(emp.get("probation_end_date")),
                    "previous_experience_years": clean_num(emp.get("previous_experience_years"), 0),
                    "previous_employer": clean_str(emp.get("previous_employer")),
                    "annual_ctc_inr": clean_num(emp.get("annual_ctc_inr")),
                    "monthly_stipend_inr": clean_num(emp.get("monthly_stipend_inr"))
                })

            # Documents
            docs = c.get("documents", [])
            for doc in docs:
                doc_id = clean_str(doc.get("document_id"), f"DOC-{cid}-{doc.get('document_type','').replace(' ','_')}")
                conn.execute(text("""
                    INSERT INTO documents (
                        document_id, candidate_id, document_type, filename, file_format,
                        document_status, uploaded_date, verified_by, verification_date, remarks
                    ) VALUES (
                        :document_id, :candidate_id, :document_type, :filename, :file_format,
                        :document_status, :uploaded_date, :verified_by, :verification_date, :remarks
                    ) ON CONFLICT (document_id) DO UPDATE SET
                        document_status = EXCLUDED.document_status,
                        remarks = EXCLUDED.remarks;
                """), {
                    "document_id": doc_id,
                    "candidate_id": cid,
                    "document_type": clean_str(doc.get("document_type")),
                    "filename": clean_str(doc.get("filename")),
                    "file_format": clean_str(doc.get("file_format"), "pdf"),
                    "document_status": clean_str(doc.get("document_status"), "VERIFIED"),
                    "uploaded_date": clean_date(doc.get("uploaded_date")),
                    "verified_by": clean_str(doc.get("verified_by")) if doc.get("verified_by") else None,
                    "verification_date": clean_date(doc.get("verification_date")),
                    "remarks": clean_str(doc.get("remarks"), "Verified")
                })

            # Offer Letter
            ofr = c.get("offer_information") or c.get("offer_letter") or {}
            if ofr:
                conn.execute(text("""
                    INSERT INTO offer_letters (
                        offer_id, candidate_id, offer_type, offer_letter_status, offer_letter_filename,
                        offer_date, valid_until, position, department, reporting_manager_name,
                        joining_date, acceptance_status, acceptance_date, appointment_letter_status
                    ) VALUES (
                        :offer_id, :candidate_id, :offer_type, :offer_letter_status, :offer_letter_filename,
                        :offer_date, :valid_until, :position, :department, :reporting_manager_name,
                        :joining_date, :acceptance_status, :acceptance_date, :appointment_letter_status
                    ) ON CONFLICT (candidate_id) DO UPDATE SET
                        offer_letter_status = EXCLUDED.offer_letter_status,
                        position = EXCLUDED.position;
                """), {
                    "offer_id": clean_str(ofr.get("offer_id"), f"OFR-{cid}"),
                    "candidate_id": cid,
                    "offer_type": clean_str(ofr.get("offer_type"), "Employment Offer"),
                    "offer_letter_status": clean_str(ofr.get("offer_letter_status"), "Accepted"),
                    "offer_letter_filename": clean_str(ofr.get("offer_letter_filename")),
                    "offer_date": clean_date(ofr.get("offer_date")) or "2026-10-01",
                    "valid_until": clean_date(ofr.get("valid_until")) or "2026-10-10",
                    "position": clean_str(ofr.get("position")),
                    "department": clean_str(ofr.get("department")),
                    "reporting_manager_name": clean_str(ofr.get("reporting_manager_name")),
                    "joining_date": clean_date(ofr.get("joining_date")) or "2026-10-15",
                    "acceptance_status": clean_str(ofr.get("acceptance_status"), "Accepted"),
                    "acceptance_date": clean_date(ofr.get("acceptance_date")),
                    "appointment_letter_status": clean_str(ofr.get("appointment_letter_status"), "Issued")
                })

            # Onboarding Checklist
            chk = c.get("onboarding_checklist", [])
            for item in chk:
                conn.execute(text("""
                    INSERT INTO onboarding_checklist (
                        checklist_id, candidate_id, item_no, item_name, status, responsible,
                        due_date, completion_date, remarks
                    ) VALUES (
                        :checklist_id, :candidate_id, :item_no, :item_name, :status, :responsible,
                        :due_date, :completion_date, :remarks
                    ) ON CONFLICT (checklist_id) DO UPDATE SET
                        status = EXCLUDED.status;
                """), {
                    "checklist_id": clean_str(item.get("checklist_id"), f"CHK-{cid}-{item.get('item_no')}"),
                    "candidate_id": cid,
                    "item_no": int(item.get("item_no") or 1),
                    "item_name": clean_str(item.get("item_name")),
                    "status": clean_str(item.get("status"), "COMPLETED"),
                    "responsible": clean_str(item.get("responsible"), "HR Operations"),
                    "due_date": clean_date(item.get("due_date")) or "2026-10-15",
                    "completion_date": clean_date(item.get("completion_date")),
                    "remarks": clean_str(item.get("remarks"), "Done")
                })

            # HR Verification summary
            hrv = c.get("hr_verification", {})
            if hrv:
                conn.execute(text("""
                    INSERT INTO hr_verification (
                        verification_id, candidate_id, hr_verification_status, manager_verification_status,
                        document_verification_status, background_verification_status,
                        overall_onboarding_status, missing_documents, hr_remarks, manager_remarks,
                        hr_verified_date, manager_verified_date, last_updated
                    ) VALUES (
                        :verification_id, :candidate_id, :hr_verification_status, :manager_verification_status,
                        :document_verification_status, :background_verification_status,
                        :overall_onboarding_status, :missing_documents, :hr_remarks, :manager_remarks,
                        :hr_verified_date, :manager_verified_date, :last_updated
                    ) ON CONFLICT (candidate_id) DO UPDATE SET
                        overall_onboarding_status = EXCLUDED.overall_onboarding_status;
                """), {
                    "verification_id": clean_str(hrv.get("verification_id"), f"VER-{cid}"),
                    "candidate_id": cid,
                    "hr_verification_status": clean_str(hrv.get("hr_verification_status"), "Verified"),
                    "manager_verification_status": clean_str(hrv.get("manager_verification_status"), "Approved"),
                    "document_verification_status": clean_str(hrv.get("document_verification_status"), "All Documents Verified"),
                    "background_verification_status": clean_str(hrv.get("background_verification_status"), "Passed"),
                    "overall_onboarding_status": clean_str(hrv.get("overall_onboarding_status"), "Onboarding Complete"),
                    "missing_documents": clean_str(hrv.get("missing_documents"), "None"),
                    "hr_remarks": clean_str(hrv.get("hr_remarks"), "Approved"),
                    "manager_remarks": clean_str(hrv.get("manager_remarks"), "Approved"),
                    "hr_verified_date": clean_date(hrv.get("hr_verified_date")),
                    "manager_verified_date": clean_date(hrv.get("manager_verified_date")),
                    "last_updated": clean_date(hrv.get("last_updated")) or "2026-10-03"
                })

        conn.commit()
        print("All Candidates, Documents, Offer Letters, and Child records committed to PostgreSQL Task Management database successfully!")

    # 4. Copy Generated Documents into Backend
    print("Setting up backend uploads/documents directory...")
    os.makedirs(BACKEND_DOCS_DEST, exist_ok=True)
    if os.path.exists(DOCS_SRC_DIR):
        total_copied = 0
        for root, dirs, files in os.walk(DOCS_SRC_DIR):
            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(BACKEND_DOCS_DEST, file)
                if not os.path.exists(dest_file):
                    shutil.copy2(src_file, dest_file)
                    total_copied += 1
        print(f"Copied {total_copied} candidate document files into {BACKEND_DOCS_DEST}")

if __name__ == "__main__":
    setup_database_and_load()
