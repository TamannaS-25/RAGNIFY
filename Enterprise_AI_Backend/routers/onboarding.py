from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import os
import re
from datetime import date, datetime
from uuid import uuid4

router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding & Applications"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# DEPARTMENT KEYWORDS & RESUME ATS MATCHING SCANNER
# 5 to 6 core industry keywords per department
# ============================================================

DEPARTMENT_KEYWORD_SPECS = {
    "ENGINEERING": [
        ("Python", [r"\bpython\b", r"\bpy\b"]),
        ("JavaScript", [r"\bjavascript\b", r"\bjs\b", r"\btypescript\b", r"\bts\b"]),
        ("React", [r"\breact\b", r"\breact\.js\b", r"\bfrontend\b"]),
        ("FastAPI", [r"\bfastapi\b", r"\bapi\b", r"\bapis\b", r"\bbackend\b"]),
        ("SQL", [r"\bsql\b", r"\bpostgresql\b", r"\bpostgres\b", r"\bmysql\b", r"\bdatabase\b"]),
        ("Git", [r"\bgit\b", r"\bgithub\b", r"\bversion control\b"])
    ],
    "AI & DATA SCIENCE": [
        ("Python", [r"\bpython\b", r"\bpy\b"]),
        ("Machine Learning", [r"\bmachine learning\b", r"\bml\b", r"\bdata science\b", r"\bdata analyst\b", r"\bdata & ai\b"]),
        ("PyTorch", [r"\bpytorch\b", r"\btensorflow\b", r"\bscikit\b", r"\bsklearn\b", r"\bkeras\b"]),
        ("Deep Learning", [r"\bdeep learning\b", r"\bdl\b", r"\bneural\b"]),
        ("NLP", [r"\bnlp\b", r"\bnatural language\b", r"\bllm\b", r"\btransformers\b"]),
        ("Pandas", [r"\bpandas\b", r"\bnumpy\b", r"\bjupyter\b", r"\bbi dashboard\b", r"\bpower bi\b", r"\btableau\b"])
    ],
    "PRODUCT & DESIGN": [
        ("Figma", [r"\bfigma\b", r"\badobe\b", r"\bsketch\b"]),
        ("UI/UX", [r"\bui/ux\b", r"\bui\b", r"\bux\b", r"\buser interface\b", r"\bdesign\b"]),
        ("Wireframing", [r"\bwireframing\b", r"\bwireframes\b", r"\bmockup\b"]),
        ("User Research", [r"\buser research\b", r"\busability\b", r"\buser testing\b"]),
        ("Prototyping", [r"\bprototyping\b", r"\bprototype\b", r"\binteraction\b"]),
        ("Design System", [r"\bdesign system\b", r"\bstyle guide\b", r"\bvisual design\b"])
    ],
    "INFRASTRUCTURE": [
        ("Docker", [r"\bdocker\b", r"\bcontainer\b", r"\bcontainers\b"]),
        ("Kubernetes", [r"\bkubernetes\b", r"\bk8s\b"]),
        ("AWS", [r"\baws\b", r"\bcloud\b", r"\bazure\b", r"\bgcp\b"]),
        ("CI/CD", [r"\bci/cd\b", r"\bcicd\b", r"\bpipeline\b", r"\bjenkins\b"]),
        ("Linux", [r"\blinux\b", r"\bbash\b", r"\bshell\b", r"\bubuntu\b"]),
        ("Terraform", [r"\bterraform\b", r"\biac\b", r"\binfrastructure\b"])
    ],
    "FINANCE & ACCOUNTS": [
        ("Accounting", [r"\baccounting\b", r"\baccountant\b", r"\bledger\b", r"\bfinance\b", r"\bfinancial\b"]),
        ("Financial Modeling", [r"\bfinancial modeling\b", r"\bforecasting\b", r"\bvaluation\b"]),
        ("Budgeting", [r"\bbudgeting\b", r"\bbudget\b", r"\bcost control\b"]),
        ("Auditing", [r"\bauditing\b", r"\baudit\b", r"\bcompliance\b"]),
        ("Taxation", [r"\btaxation\b", r"\btax\b", r"\bgst\b", r"\btds\b"]),
        ("Excel", [r"\bexcel\b", r"\bspreadsheets\b", r"\berp\b", r"\btally\b", r"\bsap\b"])
    ],
    "SALES & MARKETING": [
        ("SEO", [r"\bseo\b", r"\bsearch engine\b"]),
        ("Lead Generation", [r"\blead generation\b", r"\bleads\b", r"\binbound\b", r"\boutbound\b"]),
        ("Digital Marketing", [r"\bdigital marketing\b", r"\bsocial media\b", r"\bmarketing\b"]),
        ("CRM", [r"\bcrm\b", r"\bhubspot\b", r"\bsalesforce\b"]),
        ("Content Strategy", [r"\bcontent strategy\b", r"\bcopywriting\b", r"\bcontent\b"]),
        ("Campaign Management", [r"\bcampaign management\b", r"\bcampaign\b", r"\badvertising\b", r"\bads\b"])
    ],
    "HR & ADMIN": [
        ("Talent Acquisition", [r"\btalent acquisition\b", r"\brecruitment\b", r"\bhiring\b", r"\bsourcing\b"]),
        ("Onboarding", [r"\bonboarding\b", r"\binduction\b", r"\borientation\b"]),
        ("Payroll", [r"\bpayroll\b", r"\bcompensation\b", r"\bbenefits\b"]),
        ("Compliance", [r"\bcompliance\b", r"\blabor laws\b", r"\bpolicy\b"]),
        ("Employee Relations", [r"\bemployee relations\b", r"\bengagement\b", r"\bretention\b"]),
        ("HRIS", [r"\bhris\b", r"\bhrms\b", r"\bpeople operations\b", r"\bhr\b"])
    ],
    "QA & TESTING": [
        ("Test Automation", [r"\btest automation\b", r"\bautomation\b", r"\bqa\b", r"\bquality assurance\b"]),
        ("Selenium", [r"\bselenium\b", r"\bcypress\b", r"\bplaywright\b"]),
        ("API Testing", [r"\bapi testing\b", r"\bpostman\b", r"\brest api\b", r"\bapis\b"]),
        ("Bug Tracking", [r"\bbug tracking\b", r"\bjira\b", r"\bdefect\b", r"\bissue tracking\b"]),
        ("Manual Testing", [r"\bmanual testing\b", r"\btest execution\b", r"\bblack box\b"]),
        ("Test Cases", [r"\btest cases\b", r"\btest plan\b", r"\btest scenarios\b", r"\btest coverage\b"])
    ]
}


def resolve_department_key(dept_name: str) -> str:
    d = (dept_name or "").upper()
    if "AI" in d or "DATA" in d or "MACHINE" in d:
        return "AI & DATA SCIENCE"
    elif "DESIGN" in d or "PRODUCT" in d or "UI" in d or "UX" in d:
        return "PRODUCT & DESIGN"
    elif "INFRA" in d or "DEVOPS" in d or "CLOUD" in d:
        return "INFRASTRUCTURE"
    elif "FINANCE" in d or "ACCOUNT" in d:
        return "FINANCE & ACCOUNTS"
    elif "MARKET" in d or "SALE" in d or "GROWTH" in d:
        return "SALES & MARKETING"
    elif "HR" in d or "PEOPLE" in d or "ADMIN" in d:
        return "HR & ADMIN"
    elif "QA" in d or "TEST" in d or "QUALITY" in d:
        return "QA & TESTING"
    return "ENGINEERING"


def scan_resume_and_calculate_match(candidate_id: str, department: str, cand_docs: list, extra_context: list = None) -> dict:
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "documents")
    dept_key = resolve_department_key(department)
    specs = DEPARTMENT_KEYWORD_SPECS.get(dept_key, DEPARTMENT_KEYWORD_SPECS["ENGINEERING"])
    keyword_names = [kw for kw, _ in specs]

    extracted_text = ""

    # 1. Search in candidate's registered documents list
    resume_doc = None
    for d in cand_docs:
        dtype = (getattr(d, "document_type", None) or getattr(d, "documentType", "") or "").lower()
        fname = (getattr(d, "filename", None) or getattr(d, "fileName", "") or "").lower()
        if "resume" in dtype or "cv" in dtype or "resume" in fname or "cv" in fname:
            resume_doc = d
            break

    if resume_doc:
        actual_fname = getattr(resume_doc, "filename", None) or getattr(resume_doc, "fileName", "")
        if actual_fname:
            fpath = os.path.join(docs_dir, actual_fname)
            if os.path.exists(fpath):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(fpath)
                    extracted_text = " ".join([page.extract_text() or "" for page in reader.pages])
                except Exception as e:
                    print(f"Error reading PDF resume {fpath}: {e}")

    # 2. If no text yet, search directly on filesystem for {candidate_id}_Resume.pdf
    if not extracted_text and os.path.exists(docs_dir):
        for f in os.listdir(docs_dir):
            if f.startswith(f"{candidate_id}_") and ("resume" in f.lower() or "cv" in f.lower()):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(os.path.join(docs_dir, f))
                    extracted_text = " ".join([page.extract_text() or "" for page in reader.pages])
                    if extracted_text:
                        break
                except Exception:
                    pass

    # 3. Combine with profile context (skills, role, department)
    search_corpus = extracted_text
    if extra_context:
        search_corpus += " " + " ".join([str(x) for x in extra_context if x])

    corpus_lower = search_corpus.lower()

    matched = []
    missing = []

    for kw, patterns in specs:
        is_match = False
        for pat in patterns:
            if re.search(pat, corpus_lower, re.IGNORECASE):
                is_match = True
                break
        if is_match:
            matched.append(kw)
        else:
            missing.append(kw)

    score = round((len(matched) / len(specs)) * 100) if specs else 0

    if score >= 70:
        recommendation = "Strong Match — Candidate resume exhibits high departmental competency. Recommended for Approval."
        status_label = "HIGH_MATCH"
    elif score >= 50:
        recommendation = "Moderate Match — Partial alignment with core keywords. Manual review recommended before decision."
        status_label = "MODERATE_MATCH"
    else:
        recommendation = "Low Match — Candidate resume lacks essential departmental keywords. High risk of mismatch."
        status_label = "LOW_MATCH"

    return {
        "resumeScore": score,
        "matchedKeywords": matched,
        "missingKeywords": missing,
        "departmentKeywords": keyword_names,
        "scannedDepartment": dept_key,
        "atsRecommendation": recommendation,
        "matchStatus": status_label,
        "hasResumeScanned": bool(extracted_text)
    }


def delete_candidate_application(candidate_id: str, db: Session):
    """
    Permanently and automatically deletes a candidate application, all associated
    compliance documents, physical uploaded files on disk, and database rows across all tables.
    """
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "documents")

    # 1. Clean up physical document files on disk
    try:
        cand_docs = db.query(models.Document).filter(models.Document.candidate_id == candidate_id).all()
        for d in cand_docs:
            if d.filename:
                fpath = os.path.join(docs_dir, d.filename)
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception as err:
                        print(f"Warning: could not delete file {fpath}: {err}")

        if os.path.exists(docs_dir):
            for fname in os.listdir(docs_dir):
                if fname.startswith(f"{candidate_id}_"):
                    fpath = os.path.join(docs_dir, fname)
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
    except Exception as e:
        print(f"File cleanup error for candidate {candidate_id}: {e}")

    # 2. Delete linked DB records in order of foreign key relationships
    try:
        # Documents
        db.query(models.Document).filter(models.Document.candidate_id == candidate_id).delete(synchronize_session=False)
        # HR Verification
        db.query(models.HRVerification).filter(models.HRVerification.candidate_id == candidate_id).delete(synchronize_session=False)
        # Offer Letters
        db.query(models.OfferLetter).filter(models.OfferLetter.candidate_id == candidate_id).delete(synchronize_session=False)
        # Onboarding Checklist
        db.query(models.OnboardingChecklist).filter(models.OnboardingChecklist.candidate_id == candidate_id).delete(synchronize_session=False)
        # Working Hours
        db.query(models.WorkingHours).filter(models.WorkingHours.candidate_id == candidate_id).delete(synchronize_session=False)
        # Internship Tenure
        db.query(models.InternshipTenure).filter(models.InternshipTenure.candidate_id == candidate_id).delete(synchronize_session=False)
        # Employment Details
        db.query(models.EmploymentDetails).filter(models.EmploymentDetails.candidate_id == candidate_id).delete(synchronize_session=False)
        # Education
        db.query(models.Education).filter(models.Education.candidate_id == candidate_id).delete(synchronize_session=False)
        # Emergency Contacts
        db.query(models.EmergencyContact).filter(models.EmergencyContact.candidate_id == candidate_id).delete(synchronize_session=False)
        # Address
        db.query(models.Address).filter(models.Address.candidate_id == candidate_id).delete(synchronize_session=False)
        # Contact Details
        db.query(models.ContactDetails).filter(models.ContactDetails.candidate_id == candidate_id).delete(synchronize_session=False)
        # Attendance Records
        db.query(models.AttendanceRecord).filter(models.AttendanceRecord.candidate_id == candidate_id).delete(synchronize_session=False)
        # User accounts (if any created for this candidate)
        db.query(models.User).filter((models.User.user_id == candidate_id) | (models.User.employee_id == candidate_id)).delete(synchronize_session=False)
        # Candidate Profile
        cand_deleted = db.query(models.CandidateProfile).filter(models.CandidateProfile.candidate_id == candidate_id).delete(synchronize_session=False)

        db.commit()
        return {"success": True, "candidate_id": candidate_id, "deleted_count": cand_deleted}
    except Exception as e:
        db.rollback()
        print(f"Error deleting candidate {candidate_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error deleting candidate application: {str(e)}")


@router.get("/applications")
def get_applications(db: Session = Depends(get_db)):
    candidates = db.query(models.CandidateProfile).all()
    results = []
    
    # Auto-delete any existing rejected applications automatically
    rejected_to_purge = []
    for c in candidates:
        hr_v = db.query(models.HRVerification).filter(models.HRVerification.candidate_id == c.candidate_id).first()
        if hr_v and ("REJECT" in (hr_v.hr_verification_status or "").upper() or "REJECT" in (hr_v.overall_onboarding_status or "").upper()):
            rejected_to_purge.append(c.candidate_id)

    for rej_id in rejected_to_purge:
        try:
            delete_candidate_application(rej_id, db)
        except Exception as e:
            print(f"Auto-purge error on rejected application {rej_id}: {e}")

    # Reload active non-rejected candidates
    if rejected_to_purge:
        candidates = db.query(models.CandidateProfile).all()

    for c in candidates:
        contact = db.query(models.ContactDetails).filter(models.ContactDetails.candidate_id == c.candidate_id).first()
        emp_det = db.query(models.EmploymentDetails).filter(models.EmploymentDetails.candidate_id == c.candidate_id).first()
        edu = db.query(models.Education).filter(models.Education.candidate_id == c.candidate_id, models.Education.is_highest_qualification == True).first()
        hr_v = db.query(models.HRVerification).filter(models.HRVerification.candidate_id == c.candidate_id).first()
        doc_count = db.query(models.Document).filter(models.Document.candidate_id == c.candidate_id).count()

        status_mapping = "PENDING"
        if hr_v:
            if "Complete" in hr_v.overall_onboarding_status or "Verified" in hr_v.hr_verification_status:
                status_mapping = "APPROVED"
            elif "Review" in hr_v.hr_verification_status or "Progress" in hr_v.overall_onboarding_status:
                status_mapping = "UNDER_REVIEW"
            else:
                status_mapping = "PENDING"

        # Query candidate's actual registered documents from database
        cand_docs = db.query(models.Document).filter(models.Document.candidate_id == c.candidate_id).all()
        doc_list = []
        for d in cand_docs:
            doc_list.append({
                "id": d.document_id,
                "documentType": d.document_type,
                "label": d.document_type,
                "name": d.filename.replace(f"{c.candidate_id}_", "") if f"{c.candidate_id}_" in d.filename else d.filename,
                "fileName": d.filename,
                "fileUrl": f"/documents/view/{d.filename}",
                "status": d.document_status,
                "category": "Identity & Government KYC" if ("Proof" in d.document_type or "Identity" in d.document_type or "PAN" in d.document_type) else ("Academic & Credentials" if ("Degree" in d.document_type or "Resume" in d.document_type) else "Corporate & Tenure"),
                "size": "1.4 MB"
            })

        dept_name = emp_det.department if emp_det else "Engineering"
        cand_skills = ["Python", "PyTorch", "FastAPI", "React"] if c.candidate_type == "Intern" else ["Architecture", "System Design", "Cloud Infrastructure", "Kubernetes"]
        role_name = emp_det.job_title if emp_det else ("AI / ML Intern" if c.candidate_type == "Intern" else "Senior Engineer")

        # Scan resume against department keywords and calculate match score
        match_data = scan_resume_and_calculate_match(
            candidate_id=c.candidate_id,
            department=dept_name,
            cand_docs=cand_docs,
            extra_context=cand_skills + [role_name, dept_name]
        )

        results.append({
            "id": c.candidate_id,
            "applicantName": c.full_name,
            "email": contact.official_email if contact else f"{c.candidate_id.lower()}@ragnify-demo.com",
            "phone": contact.mobile_number if contact else "+91 98000 00000",
            "type": c.candidate_type,
            "role": role_name,
            "department": dept_name,
            "college": edu.institution if edu else "IIT Bombay",
            "degree": edu.qualification if edu else "B.Tech Computer Science",
            "cgpa": str(edu.score_value) if edu else "8.8",
            "experienceYears": f"{emp_det.previous_experience_years} Years" if (emp_det and emp_det.previous_experience_years) else "Fresher",
            "appliedDate": str(emp_det.joining_date) if emp_det else "2026-10-02",
            "status": status_mapping,
            "resumeScore": match_data["resumeScore"],
            "matchedKeywords": match_data["matchedKeywords"],
            "missingKeywords": match_data["missingKeywords"],
            "departmentKeywords": match_data["departmentKeywords"],
            "scannedDepartment": match_data["scannedDepartment"],
            "atsRecommendation": match_data["atsRecommendation"],
            "matchStatus": match_data["matchStatus"],
            "hasResumeScanned": match_data["hasResumeScanned"],
            "documentsCount": len(doc_list),
            "documents": doc_list,
            "skills": cand_skills
        })

    return results

@router.get("/applications/{application_id}")
def get_application_by_id(application_id: str, db: Session = Depends(get_db)):
    c = db.query(models.CandidateProfile).filter(models.CandidateProfile.candidate_id == application_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Application not found")
    
    contact = db.query(models.ContactDetails).filter(models.ContactDetails.candidate_id == c.candidate_id).first()
    emp_det = db.query(models.EmploymentDetails).filter(models.EmploymentDetails.candidate_id == c.candidate_id).first()
    edu = db.query(models.Education).filter(models.Education.candidate_id == c.candidate_id, models.Education.is_highest_qualification == True).first()
    hr_v = db.query(models.HRVerification).filter(models.HRVerification.candidate_id == c.candidate_id).first()
    cand_docs = db.query(models.Document).filter(models.Document.candidate_id == c.candidate_id).all()
    
    doc_list = []
    for d in cand_docs:
        doc_list.append({
            "id": d.document_id,
            "documentType": d.document_type,
            "label": d.document_type,
            "name": d.filename.replace(f"{c.candidate_id}_", "") if f"{c.candidate_id}_" in d.filename else d.filename,
            "fileName": d.filename,
            "fileUrl": f"/documents/view/{d.filename}",
            "status": d.document_status,
            "category": "Identity & Government KYC" if ("Proof" in d.document_type or "Identity" in d.document_type or "PAN" in d.document_type) else ("Academic & Credentials" if ("Degree" in d.document_type or "Resume" in d.document_type) else "Corporate & Tenure"),
            "size": "1.4 MB"
        })

    status_mapping = "PENDING"
    if hr_v:
        if "Complete" in hr_v.overall_onboarding_status or "Verified" in hr_v.hr_verification_status:
            status_mapping = "APPROVED"
        elif "Review" in hr_v.hr_verification_status or "Progress" in hr_v.overall_onboarding_status:
            status_mapping = "UNDER_REVIEW"

    dept_name = emp_det.department if emp_det else "Engineering"
    cand_skills = ["Python", "PyTorch", "FastAPI", "React"] if c.candidate_type == "Intern" else ["Architecture", "System Design", "Cloud Infrastructure", "Kubernetes"]
    role_name = emp_det.job_title if emp_det else ("AI / ML Intern" if c.candidate_type == "Intern" else "Senior Engineer")

    # Scan resume against department keywords and calculate match score
    match_data = scan_resume_and_calculate_match(
        candidate_id=c.candidate_id,
        department=dept_name,
        cand_docs=cand_docs,
        extra_context=cand_skills + [role_name, dept_name]
    )

    return {
        "id": c.candidate_id,
        "applicantName": c.full_name,
        "email": contact.official_email if contact else f"{c.candidate_id.lower()}@ragnify-demo.com",
        "phone": contact.mobile_number if contact else "+91 98000 00000",
        "type": c.candidate_type,
        "role": role_name,
        "department": dept_name,
        "college": edu.institution if edu else "IIT Bombay",
        "degree": edu.qualification if edu else "B.Tech Computer Science",
        "cgpa": str(edu.score_value) if edu else "8.8",
        "experienceYears": f"{emp_det.previous_experience_years} Years" if (emp_det and emp_det.previous_experience_years) else "Fresher",
        "appliedDate": str(emp_det.joining_date) if emp_det else "2026-10-02",
        "status": status_mapping,
        "resumeScore": match_data["resumeScore"],
        "matchedKeywords": match_data["matchedKeywords"],
        "missingKeywords": match_data["missingKeywords"],
        "departmentKeywords": match_data["departmentKeywords"],
        "scannedDepartment": match_data["scannedDepartment"],
        "atsRecommendation": match_data["atsRecommendation"],
        "matchStatus": match_data["matchStatus"],
        "hasResumeScanned": match_data["hasResumeScanned"],
        "documentsCount": len(doc_list),
        "documents": doc_list,
        "skills": cand_skills
    }


@router.post("/apply")
async def submit_application(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    uploaded_files_map = {}  # { doc_type: (orig_filename, file_bytes) }
    
    KEY_TO_DOCTYPE = {
        "resume": "Resume / CV",
        "identity_proof": "Identity Proof (Aadhaar)",
        "pan_proof": "PAN Card Proof",
        "degree_certificate": "Degree Certificate",
        "previous_employment_docs": "Previous Employment Documents",
        "offer_letter": "Offer Letter",
        "internship_certificate": "Internship Certificate"
    }

    if "multipart/form-data" in content_type:
        form = await request.form()
        cand_type = str(form.get("type", "Intern")).capitalize()
        full_name = form.get("applicantName") or "New Applicant"
        email = form.get("email") or ""
        phone = form.get("phone") or "+91 98765 00000"
        role = form.get("role") or ("Frontend Development Intern" if cand_type == "Intern" else "Software Development Engineer")
        department = form.get("department") or "Engineering"
        college = form.get("college") or "Premier Engineering Institute"
        degree = form.get("degree") or "B.Tech Computer Science"
        cgpa_val = float(form.get("cgpa") or 8.5) if form.get("cgpa") else 8.5
        exp_years = int(str(form.get("experienceYears") or "0").split()[0]) if form.get("experienceYears") else 0

        for key, val in form.items():
            if hasattr(val, "filename") and hasattr(val, "read") and val.filename:
                file_bytes = await val.read()
                if file_bytes and len(file_bytes) > 0:
                    clean_k = key.lower().replace("file_", "").replace("doc_", "")
                    doc_type = KEY_TO_DOCTYPE.get(clean_k, clean_k.replace("_", " ").title())
                    uploaded_files_map[doc_type] = (val.filename, file_bytes)
    else:
        payload = await request.json()
        cand_type = str(payload.get("type", "Intern")).capitalize()
        full_name = payload.get("applicantName") or "New Applicant"
        email = payload.get("email") or ""
        phone = payload.get("phone") or "+91 98765 00000"
        role = payload.get("role") or ("Frontend Development Intern" if cand_type == "Intern" else "Software Development Engineer")
        department = payload.get("department") or "Engineering"
        college = payload.get("college") or "Premier Engineering Institute"
        degree = payload.get("degree") or "B.Tech Computer Science"
        try:
            cgpa_val = float(payload.get("cgpa") or 8.5)
        except:
            cgpa_val = 8.5
        try:
            exp_years = int(str(payload.get("experienceYears") or "0").split()[0])
        except:
            exp_years = 0

    if cand_type not in ["Intern", "Employee"]:
        cand_type = "Intern"

    # Generate Candidate ID: e.g. INT-2026-xxxx or EMP-2026-xxxx
    prefix = "INT" if cand_type == "Intern" else "EMP"
    unique_suffix = uuid4().hex[:4].upper()
    cand_id = f"{prefix}-{datetime.now().year}-{unique_suffix}"
    today = date.today()

    if not email:
        email = f"{cand_id.lower()}@ragnify-applicant.com"

    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "documents")
    os.makedirs(docs_dir, exist_ok=True)

    # Determine photo filename if uploaded
    photo_filename = f"{cand_id}_Photograph.jpg"
    if "Passport Photograph" in uploaded_files_map:
        p_name, _ = uploaded_files_map["Passport Photograph"]
        safe_p_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', p_name)
        photo_filename = f"{cand_id}_{safe_p_name}"

    # 1. Create CandidateProfile
    new_cand = models.CandidateProfile(
        candidate_id=cand_id,
        full_name=full_name,
        gender="Other",
        date_of_birth=date(2002, 1, 1) if cand_type == "Intern" else date(1996, 1, 1),
        nationality="Indian",
        marital_status="Single",
        blood_group="O+",
        profile_photo_filename=photo_filename,
        candidate_type=cand_type,
        data_classification="Internal"
    )
    db.add(new_cand)

    # 2. Create ContactDetails
    new_contact = models.ContactDetails(
        contact_id=f"CNT-{cand_id}",
        candidate_id=cand_id,
        personal_email=email,
        official_email=email,
        mobile_number=phone,
        alternate_phone="+91 98000 00000"
    )
    db.add(new_contact)

    # 3. Create Education
    new_edu = models.Education(
        education_id=f"EDU-{cand_id}",
        candidate_id=cand_id,
        level="Undergraduate" if cand_type == "Intern" else "Postgraduate",
        qualification=degree,
        specialization="Computer Science & Engineering",
        institution=college,
        board_or_university="Autonomous University",
        year_of_passing=2026 if cand_type == "Intern" else 2022,
        score_type="CGPA",
        score_value=cgpa_val,
        education_status="Completed" if cand_type == "Employee" else "Pursuing",
        is_highest_qualification=True,
        document_filename=f"{cand_id}_Degree_Certificate.pdf",
        verification_status="Pending"
    )
    db.add(new_edu)

    # Ensure a default Manager exists for foreign key constraint
    default_mgr = db.query(models.Manager).first()
    default_mgr_id = default_mgr.manager_id if default_mgr else "MGR-001"
    default_mgr_name = (default_mgr.name or default_mgr.manager_name) if default_mgr else "Vikram Mehta"

    # Ensure a default HR Staff exists for foreign key constraint
    default_hr = db.query(models.HRStaff).first()
    if not default_hr:
        default_hr = models.HRStaff(
            hr_id="HR-101",
            hr_name="Pooja Sharma",
            hr_email="pooja.sharma@ragnify.io"
        )
        db.add(default_hr)
        db.flush()
    default_hr_id = default_hr.hr_id
    default_hr_name = default_hr.hr_name

    # 4. Create EmploymentDetails
    new_emp_det = models.EmploymentDetails(
        employment_id=f"EMP-DET-{cand_id}",
        candidate_id=cand_id,
        candidate_type=cand_type,
        job_title=role,
        department=department,
        reporting_manager_id=default_mgr_id,
        reporting_manager_name=default_mgr_name,
        hr_coordinator_id=default_hr_id,
        hr_coordinator_name=default_hr_name,
        employment_type="Internship" if cand_type == "Intern" else "Full-Time Permanent",
        work_location="Bangalore HQ",
        work_mode="Hybrid",
        joining_date=today,
        probation_months=3 if cand_type == "Employee" else 0,
        probation_end_date=None,
        previous_experience_years=exp_years,
        previous_employer="None" if cand_type == "Intern" else "Previous Tech Corp",
        annual_ctc_inr=1800000.00 if cand_type == "Employee" else None,
        monthly_stipend_inr=30000.00 if cand_type == "Intern" else None
    )
    db.add(new_emp_det)

    # 5. Create HRVerification
    new_hr_v = models.HRVerification(
        verification_id=f"VRF-{cand_id}",
        candidate_id=cand_id,
        hr_verification_status="Pending",
        manager_verification_status="Pending",
        document_verification_status="Uploaded - Awaiting Verification" if uploaded_files_map else "Pending Uploads",
        background_verification_status="Initiated",
        overall_onboarding_status="Under Review",
        missing_documents="",
        hr_remarks="Application submitted via New User portal. Verification pending.",
        manager_remarks="Candidate queue assigned for interview & review.",
        hr_verified_date=None,
        manager_verified_date=None,
        last_updated=today
    )
    db.add(new_hr_v)

    # 6. Save ONLY authentic original files uploaded by applicant - NO fake documents!
    doc_idx = 1
    for doc_type, (orig_filename, file_bytes) in uploaded_files_map.items():
        safe_orig_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', orig_filename)
        actual_file_name = f"{cand_id}_{safe_orig_name}"
        target_path = os.path.join(docs_dir, actual_file_name)

        with open(target_path, "wb") as f_out:
            f_out.write(file_bytes)

        ext = safe_orig_name.split(".")[-1].upper() if "." in safe_orig_name else "PDF"
        doc_obj = models.Document(
            document_id=f"DOC-{cand_id}-{doc_idx:02d}",
            candidate_id=cand_id,
            document_type=doc_type,
            filename=actual_file_name,
            file_format=ext,
            document_status="PENDING",
            uploaded_date=today,
            verified_by=None,
            verification_date=None,
            remarks="Original document uploaded by applicant."
        )
        db.add(doc_obj)
        doc_idx += 1

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error persisting application to DB: {e}")
        raise HTTPException(status_code=500, detail=f"Database error persisting application: {str(e)}")

    return {
        "id": cand_id,
        "applicantName": full_name,
        "email": email,
        "phone": phone,
        "type": cand_type,
        "role": role,
        "department": department,
        "status": "PENDING",
        "submissionDate": str(today),
        "documentsCount": len(uploaded_files_map),
        "message": f"{cand_type} application submitted successfully with {len(uploaded_files_map)} original document(s)!"
    }


@router.patch("/applications/{application_id}")
def update_application_status(application_id: str, payload: dict, db: Session = Depends(get_db)):
    from datetime import date
    new_status = payload.get("status", "UNDER_REVIEW")
    notes = payload.get("notes", "Reviewed by HR Operations")

    # If status is REJECTED, automatically delete the application completely
    if new_status.upper() == "REJECTED":
        delete_candidate_application(application_id, db)
        return {
            "success": True,
            "id": application_id,
            "status": "REJECTED",
            "deleted": True,
            "message": f"Application {application_id} has been rejected and permanently deleted automatically."
        }

    hr_v = db.query(models.HRVerification).filter(models.HRVerification.candidate_id == application_id).first()
    db_status = "Approved" if new_status.upper() == "APPROVED" else new_status
    overall_status = "Completed" if new_status.upper() == "APPROVED" else new_status

    if hr_v:
        hr_v.hr_verification_status = db_status
        hr_v.overall_onboarding_status = overall_status
        hr_v.hr_remarks = notes
        hr_v.last_updated = date.today()
    else:
        new_hr_v = models.HRVerification(
            verification_id=f"VRF-{application_id}",
            candidate_id=application_id,
            hr_verification_status=db_status,
            manager_verification_status="Pending",
            document_verification_status="Verified" if new_status.upper() == "APPROVED" else "Under Review",
            background_verification_status="Verified" if new_status.upper() == "APPROVED" else "Under Review",
            overall_onboarding_status=overall_status,
            missing_documents="",
            hr_remarks=notes,
            manager_remarks="",
            last_updated=date.today()
        )
        db.add(new_hr_v)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error updating application status in DB: {e}")

    return {"success": True, "id": application_id, "status": new_status}


@router.delete("/applications/{application_id}")
def delete_application(application_id: str, db: Session = Depends(get_db)):
    """
    Explicit deletion endpoint for candidate application.
    """
    res = delete_candidate_application(application_id, db)
    return {
        "success": True,
        "id": application_id,
        "deleted": True,
        "message": f"Application {application_id} has been permanently deleted."
    }
