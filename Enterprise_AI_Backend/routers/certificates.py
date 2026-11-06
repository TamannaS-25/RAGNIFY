import os
import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import SessionLocal
import models

router = APIRouter(
    prefix="/certificates",
    tags=["Milestone & Completion Certificates"]
)

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "documents")
os.makedirs(DOCS_DIR, exist_ok=True)
APPROVAL_STATE_FILE = os.path.join(DOCS_DIR, "certificate_approvals.json")


def _load_approval_state() -> dict:
    if os.path.exists(APPROVAL_STATE_FILE):
        try:
            with open(APPROVAL_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "approved": set(data.get("approved", [])),
                    "revoked": set(data.get("revoked", []))
                }
        except Exception:
            pass
    return {"approved": set(), "revoked": set()}


def _save_approval_state(approved_set: set, revoked_set: set):
    try:
        with open(APPROVAL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "approved": sorted(list(approved_set)),
                "revoked": sorted(list(revoked_set))
            }, f, indent=2)
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def get_certificates(db: Session = Depends(get_db)):
    state = _load_approval_state()
    approved_ids = state["approved"]
    revoked_ids = state["revoked"]

    candidates = db.query(models.CandidateProfile).all()
    results = []

    # 1. Always include the active Intern Portal user: Ananya Roy (INT-201 / intern@ragnify.com)
    int201_approved = ("INT-201" in approved_ids or "CERT-INT-201" in approved_ids) and ("INT-201" not in revoked_ids)
    results.append({
        "id": "CERT-INT-201",
        "candidateId": "INT-201",
        "candidateName": "Ananya Roy",
        "internName": "Ananya Roy",
        "candidateEmail": "intern@ragnify.com",
        "email": "intern@ragnify.com",
        "type": "Intern",
        "certificateType": "Internship Completion Certificate",
        "role": "Frontend Development Intern",
        "department": "Frontend Engineering",
        "mentorName": "Vikram Mehta",
        "internshipPeriod": "2026-08-01 to 2026-10-31 (3 Months)",
        "tenureDuration": "2026-08-01 to 2026-10-31 (3 Months)",
        "daysCompleted": 92 if int201_approved else 68,
        "totalDays": 92,
        "progress": 100 if int201_approved else 74,
        "tenureStatus": "COMPLETED" if int201_approved else "IN_PROGRESS",
        "certificateStatus": "AVAILABLE" if int201_approved else "LOCKED",
        "status": "AVAILABLE" if int201_approved else "LOCKED",
        "hrApproved": int201_approved,
        "internAccessGranted": int201_approved,
        "issueDate": str(date.today()) if int201_approved else "Awaiting Completion & HR Approval",
        "fileName": "INT-201_Certificate.pdf",
        "fileUrl": "/certificates/download/CERT-INT-201"
    })

    for idx, c in enumerate(candidates):
        if c.candidate_id == "INT-201":
            continue
        contact = db.query(models.ContactDetails).filter(models.ContactDetails.candidate_id == c.candidate_id).first()
        emp_det = db.query(models.EmploymentDetails).filter(models.EmploymentDetails.candidate_id == c.candidate_id).first()
        tenure = db.query(models.InternshipTenure).filter(models.InternshipTenure.candidate_id == c.candidate_id).first()

        cert_id = f"CERT-{c.candidate_id}"
        is_intern = (c.candidate_type == "Intern")

        is_explicit_approved = (cert_id in approved_ids or c.candidate_id in approved_ids)
        is_explicit_revoked = (cert_id in revoked_ids or c.candidate_id in revoked_ids)

        if is_explicit_revoked:
            tenure_status = "IN_PROGRESS" if is_intern else "COMPLETED"
            cert_status = "LOCKED"
            progress_pct = 74 if is_intern else 90
            hr_approved = False
            issue_date = "Access Locked by HR"
        elif is_explicit_approved:
            tenure_status = "COMPLETED"
            cert_status = "AVAILABLE"
            progress_pct = 100
            hr_approved = True
            issue_date = str(date.today())
        elif idx % 3 == 0 and not is_intern:
            # Employees who completed probation
            tenure_status = "COMPLETED"
            cert_status = "AVAILABLE"
            progress_pct = 100
            hr_approved = True
            issue_date = "2026-10-05"
        elif idx % 3 == 1:
            tenure_status = "COMPLETED"
            cert_status = "UPCOMING"
            progress_pct = 100
            hr_approved = False
            issue_date = "Ready for HR Sign-Off"
        else:
            tenure_status = "IN_PROGRESS"
            cert_status = "LOCKED"
            progress_pct = 65
            hr_approved = False
            issue_date = "Pending Tenure Completion"

        if is_intern:
            start_str = str(tenure.internship_start_date) if tenure else "2026-07-15"
            end_str = str(tenure.internship_end_date) if tenure else "2026-10-15"
            duration_label = f"{start_str} to {end_str} (3 Months)"
            cert_type_label = "Internship Completion Certificate"
        else:
            join_str = str(emp_det.joining_date) if (emp_det and emp_det.joining_date) else "2026-06-01"
            duration_label = f"Joined {join_str} (3-Month Probation)"
            cert_type_label = "Probation Confirmation & Service Award"

        file_name = f"{c.candidate_id}_Certificate.pdf"

        results.append({
            "id": cert_id,
            "candidateId": c.candidate_id,
            "candidateName": c.full_name,
            "internName": c.full_name,
            "candidateEmail": contact.official_email if contact else f"{c.candidate_id.lower()}@ragnify.com",
            "email": contact.official_email if contact else f"{c.candidate_id.lower()}@ragnify.com",
            "type": c.candidate_type,
            "certificateType": cert_type_label,
            "role": emp_det.job_title if emp_det else ("AI / ML Intern" if is_intern else "Senior Software Engineer"),
            "department": emp_det.department if emp_det else "Engineering",
            "mentorName": emp_det.reporting_manager_name if emp_det else "Vikram Mehta",
            "internshipPeriod": duration_label,
            "tenureDuration": duration_label,
            "daysCompleted": 92 if progress_pct == 100 else int(92 * progress_pct / 100),
            "totalDays": 92,
            "progress": progress_pct,
            "tenureStatus": tenure_status,
            "certificateStatus": cert_status,
            "status": cert_status,
            "hrApproved": hr_approved,
            "internAccessGranted": hr_approved,
            "issueDate": issue_date,
            "fileName": file_name,
            "fileUrl": f"/certificates/download/{cert_id}"
        })

    return results


@router.post("/issue/{cert_or_cand_id}")
def issue_certificate(cert_or_cand_id: str, db: Session = Depends(get_db)):
    state = _load_approval_state()
    clean_id = cert_or_cand_id.replace("CERT-", "")
    full_cert_id = f"CERT-{clean_id}"

    state["approved"].add(clean_id)
    state["approved"].add(full_cert_id)
    state["revoked"].discard(clean_id)
    state["revoked"].discard(full_cert_id)
    _save_approval_state(state["approved"], state["revoked"])

    return {
        "success": True,
        "id": full_cert_id,
        "candidateId": clean_id,
        "certificateStatus": "AVAILABLE",
        "tenureStatus": "COMPLETED",
        "progress": 100,
        "daysCompleted": 92,
        "totalDays": 92,
        "hrApproved": True,
        "internAccessGranted": True,
        "issueDate": str(date.today()),
        "status": "AVAILABLE",
        "message": f"Official Certificate of Completion approved and unlocked for {clean_id}."
    }


@router.post("/revoke/{cert_or_cand_id}")
def revoke_certificate_access(cert_or_cand_id: str, db: Session = Depends(get_db)):
    state = _load_approval_state()
    clean_id = cert_or_cand_id.replace("CERT-", "")
    full_cert_id = f"CERT-{clean_id}"

    state["approved"].discard(clean_id)
    state["approved"].discard(full_cert_id)
    state["revoked"].add(clean_id)
    state["revoked"].add(full_cert_id)
    _save_approval_state(state["approved"], state["revoked"])

    return {
        "success": True,
        "id": full_cert_id,
        "candidateId": clean_id,
        "certificateStatus": "LOCKED",
        "tenureStatus": "IN_PROGRESS",
        "progress": 74,
        "daysCompleted": 68,
        "totalDays": 92,
        "hrApproved": False,
        "internAccessGranted": False,
        "issueDate": "Awaiting Completion & HR Approval",
        "status": "LOCKED",
        "message": f"Certificate access locked for {clean_id}. Intern can no longer view or download until HR re-approves."
    }


@router.get("/download/{cert_or_cand_id}")
def download_certificate_pdf(cert_or_cand_id: str, db: Session = Depends(get_db)):
    clean_id = cert_or_cand_id.replace("CERT-", "")
    cand = db.query(models.CandidateProfile).filter(models.CandidateProfile.candidate_id == clean_id).first()
    emp_det = db.query(models.EmploymentDetails).filter(models.EmploymentDetails.candidate_id == clean_id).first()
    tenure = db.query(models.InternshipTenure).filter(models.InternshipTenure.candidate_id == clean_id).first()

    # Fallback lookup for mock IDs like CERT-9901 and INT-201
    mock_lookup = {
        "INT-201": ("Ananya Roy", "Intern", "Frontend Development Intern", "Frontend Engineering", "Vikram Mehta", "Aug 01, 2026 – Oct 31, 2026"),
        "9901": ("Ananya Roy", "Intern", "Frontend Development Intern", "Engineering", "Priya Nair", "Aug 01, 2026 – Oct 31, 2026"),
        "9902": ("Rohan Gupta", "Intern", "AI Research Intern", "AI & Data Science", "Priya Nair", "Aug 15, 2026 – Nov 15, 2026"),
        "9903": ("Sanjay Kumar", "Intern", "Backend Engineering Intern", "Engineering", "Priya Nair", "May 01, 2026 – Jul 31, 2026"),
        "9904": ("Vikram Singh", "Employee", "Senior Backend Engineer", "Engineering", "Priya Nair", "Jan 15, 2025 – Jul 15, 2025"),
        "9905": ("Sneha Reddy", "Employee", "Product Designer", "Product & Design", "Priya Nair", "Mar 10, 2025 – Sep 10, 2025"),
    }

    if cand:
        full_name = cand.full_name
        cand_type = cand.candidate_type or "Intern"
        role = emp_det.job_title if emp_det else ("Frontend Development Intern" if cand_type == "Intern" else "Senior Software Engineer")
        dept = emp_det.department if emp_det else "Engineering"
        mgr = emp_det.reporting_manager_name if emp_det else "Vikram Mehta"
        if cand_type == "Intern" and tenure:
            period_str = f"{tenure.internship_start_date} to {tenure.internship_end_date}"
        elif emp_det and emp_det.joining_date:
            period_str = f"Joined {emp_det.joining_date}"
        else:
            period_str = "Aug 01, 2026 – Oct 31, 2026"
    elif clean_id in mock_lookup:
        full_name, cand_type, role, dept, mgr, period_str = mock_lookup[clean_id]
    else:
        full_name = "Ananya Roy"
        cand_type = "Intern"
        role = "Frontend Development Intern"
        dept = "Engineering"
        mgr = "Vikram Mehta"
        period_str = "Aug 01, 2026 – Oct 31, 2026"

    pdf_filename = f"{clean_id}_Official_Certificate.pdf"
    pdf_path = os.path.join(DOCS_DIR, pdf_filename)

    try:
        import math
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors

        c = canvas.Canvas(pdf_path, pagesize=landscape(letter))
        width, height = landscape(letter)  # 792 x 612

        navy_dark = colors.HexColor('#0A192F')
        navy_mid = colors.HexColor('#1E3A8A')
        gold_primary = colors.HexColor('#C5A059')
        gold_dark = colors.HexColor('#9A7B38')
        gold_light = colors.HexColor('#F3E5AB')
        ivory_bg = colors.HexColor('#FDFBF7')
        slate_text = colors.HexColor('#334155')
        muted_text = colors.HexColor('#64748B')

        # 1. Warm Ivory Parchment Background
        c.setFillColor(ivory_bg)
        c.rect(0, 0, width, height, fill=True, stroke=False)

        # 2. Outer Heavy Navy Architectural Frame
        c.setStrokeColor(navy_dark)
        c.setLineWidth(10)
        c.rect(22, 22, width - 44, height - 44, fill=False, stroke=True)

        # 3. Inner Burnished Gold Double Frame
        c.setStrokeColor(gold_primary)
        c.setLineWidth(2.2)
        c.rect(32, 32, width - 64, height - 64, fill=False, stroke=True)

        c.setStrokeColor(gold_primary)
        c.setLineWidth(0.8)
        c.rect(37, 37, width - 74, height - 74, fill=False, stroke=True)

        # 4. Decorative Corner Ornaments (Navy & Gold Corner Flourishes)
        corners = [
            (37, 37, 1, 1),
            (width - 37, 37, -1, 1),
            (37, height - 37, 1, -1),
            (width - 37, height - 37, -1, -1)
        ]
        for cx, cy, dx, dy in corners:
            c.setStrokeColor(navy_dark)
            c.setLineWidth(2.5)
            c.line(cx + dx * 6, cy + dy * 6, cx + dx * 42, cy + dy * 6)
            c.line(cx + dx * 6, cy + dy * 6, cx + dx * 6, cy + dy * 42)
            c.setFillColor(gold_primary)
            c.rect(cx + dx * 10 - (4 if dx < 0 else 0), cy + dy * 10 - (4 if dy < 0 else 0), 5, 5, fill=True, stroke=False)

        # 5. Top Executive Crest & Organization Header
        crest_y = height - 78
        c.setFillColor(navy_dark)
        c.circle(width / 2, crest_y, 20, fill=True, stroke=False)
        c.setStrokeColor(gold_primary)
        c.setLineWidth(1.5)
        c.circle(width / 2, crest_y, 17, fill=False, stroke=True)
        c.setFillColor(gold_primary)
        c.setFont("Times-Bold", 16)
        c.drawCentredString(width / 2, crest_y - 5.5, "R")

        c.setFillColor(navy_dark)
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(width / 2, height - 115, "RAGNIFY ENTERPRISE TECHNOLOGIES")

        c.setFillColor(gold_dark)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(width / 2, height - 129, "OFFICIAL HUMAN RESOURCES & WORKFORCE CREDENTIAL REGISTRY")

        # Ornamental Gold Divider
        c.setStrokeColor(gold_primary)
        c.setLineWidth(1)
        c.line(width / 2 - 140, height - 140, width / 2 - 10, height - 140)
        c.line(width / 2 + 10, height - 140, width / 2 + 140, height - 140)
        p_diamond = c.beginPath()
        p_diamond.moveTo(width / 2, height - 136)
        p_diamond.lineTo(width / 2 + 5, height - 140)
        p_diamond.lineTo(width / 2, height - 144)
        p_diamond.lineTo(width / 2 - 5, height - 140)
        p_diamond.close()
        c.setFillColor(gold_primary)
        c.drawPath(p_diamond, fill=True, stroke=False)

        # 6. Certificate Main Title
        c.setFillColor(navy_dark)
        c.setFont("Times-Bold", 30)
        if cand_type == "Intern":
            c.drawCentredString(width / 2, height - 180, "CERTIFICATE OF COMPLETION")
            sub_pill = "INTERNSHIP TENURE & TECHNICAL EXCELLENCE"
        else:
            c.drawCentredString(width / 2, height - 180, "CERTIFICATE OF EXCELLENCE")
            sub_pill = "PROBATION CONFIRMATION & MILESTONE AWARD"

        # Subtitle Pill
        pill_w = 290
        c.setFillColor(navy_dark)
        c.roundRect(width / 2 - pill_w / 2, height - 206, pill_w, 18, 9, fill=True, stroke=False)
        c.setFillColor(gold_light)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(width / 2, height - 200, sub_pill)

        # 7. Presentation Line & Candidate Name
        c.setFillColor(slate_text)
        c.setFont("Times-Italic", 14)
        c.drawCentredString(width / 2, height - 235, "This official credential is proudly presented to")

        c.setFillColor(navy_mid)
        c.setFont("Times-BoldItalic", 33)
        c.drawCentredString(width / 2, height - 275, full_name)

        # Double Gold Line Under Name
        c.setStrokeColor(gold_primary)
        c.setLineWidth(1.4)
        c.line(width / 2 - 190, height - 286, width / 2 + 190, height - 286)
        c.setLineWidth(0.6)
        c.line(width / 2 - 150, height - 290, width / 2 + 150, height - 290)

        # 8. Citation Body Paragraph
        c.setFillColor(slate_text)
        c.setFont("Times-Roman", 13.5)
        if cand_type == "Intern":
            line1 = f"for successfully completing the comprehensive internship tenure as {role}"
            line2 = f"within the {dept} Department at Ragnify Enterprise Technologies ({period_str})."
            line3 = f"Under the technical mentorship of {mgr}, the candidate demonstrated exceptional engineering"
            line4 = "rigor, strong problem-solving aptitude, and steadfast commitment to production deliverables."
        else:
            line1 = f"for successfully completing the enterprise probation & milestone evaluation as {role}"
            line2 = f"within the {dept} Department at Ragnify Enterprise Technologies ({period_str})."
            line3 = f"Reporting to {mgr}, the candidate consistently exceeded core engineering, architectural,"
            line4 = "and organizational compliance benchmarks with distinction and leadership."

        c.drawCentredString(width / 2, height - 318, line1)
        c.drawCentredString(width / 2, height - 338, line2)
        c.drawCentredString(width / 2, height - 360, line3)
        c.drawCentredString(width / 2, height - 378, line4)

        # 9. Key Verified Metadata Pill Boxes (Role, Department, Tenure)
        box_y = height - 425
        box_w = 185
        box_h = 34
        gap = 20
        start_x = width / 2 - (box_w * 1.5 + gap)

        meta_items = [
            ("DESIGNATION", role[:28]),
            ("DEPARTMENT", dept[:28]),
            ("VERIFIED TENURE", period_str[:28])
        ]
        for idx_m, (m_label, m_val) in enumerate(meta_items):
            bx = start_x + idx_m * (box_w + gap)
            c.setFillColor(colors.HexColor('#F8FAFC'))
            c.setStrokeColor(colors.HexColor('#E2E8F0'))
            c.setLineWidth(1)
            c.roundRect(bx, box_y, box_w, box_h, 5, fill=True, stroke=True)
            c.setFillColor(muted_text)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(bx + box_w / 2, box_y + 22, m_label)
            c.setFillColor(navy_dark)
            c.setFont("Helvetica-Bold", 9.5)
            c.drawCentredString(bx + box_w / 2, box_y + 8, m_val)

        # 10. Left & Right Signature Blocks + Center Gold Embossed Seal
        sig_y = 95

        # Left Signature (HR Head)
        left_cx = 175
        c.setFillColor(navy_mid)
        c.setFont("Times-BoldItalic", 18)
        c.drawCentredString(left_cx, sig_y + 22, "Priya Sharma")
        c.setStrokeColor(navy_dark)
        c.setLineWidth(1)
        c.line(left_cx - 85, sig_y + 14, left_cx + 85, sig_y + 14)
        c.setFillColor(navy_dark)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(left_cx, sig_y + 1, "PRIYA SHARMA")
        c.setFillColor(muted_text)
        c.setFont("Helvetica", 8.5)
        c.drawCentredString(left_cx, sig_y - 11, "Head of People & HR Operations")

        # Right Signature (Mentor / Engineering Manager)
        right_cx = width - 175
        c.setFillColor(navy_mid)
        c.setFont("Times-BoldItalic", 18)
        c.drawCentredString(right_cx, sig_y + 22, mgr)
        c.setStrokeColor(navy_dark)
        c.setLineWidth(1)
        c.line(right_cx - 85, sig_y + 14, right_cx + 85, sig_y + 14)
        c.setFillColor(navy_dark)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(right_cx, sig_y + 1, mgr.upper())
        c.setFillColor(muted_text)
        c.setFont("Helvetica", 8.5)
        c.drawCentredString(right_cx, sig_y - 11, "Engineering Manager & Mentor")

        # Center Embossed Gold Seal & Ribbons
        seal_cx = width / 2
        seal_cy = sig_y + 14

        # Ribbons beneath seal
        r_left = c.beginPath()
        r_left.moveTo(seal_cx - 14, seal_cy - 15)
        r_left.lineTo(seal_cx - 26, seal_cy - 52)
        r_left.lineTo(seal_cx - 15, seal_cy - 45)
        r_left.lineTo(seal_cx - 6, seal_cy - 54)
        r_left.lineTo(seal_cx - 2, seal_cy - 15)
        r_left.close()
        c.setFillColor(navy_dark)
        c.drawPath(r_left, fill=True, stroke=False)

        r_right = c.beginPath()
        r_right.moveTo(seal_cx + 14, seal_cy - 15)
        r_right.lineTo(seal_cx + 26, seal_cy - 52)
        r_right.lineTo(seal_cx + 15, seal_cy - 45)
        r_right.lineTo(seal_cx + 6, seal_cy - 54)
        r_right.lineTo(seal_cx + 2, seal_cy - 15)
        r_right.close()
        c.setFillColor(gold_dark)
        c.drawPath(r_right, fill=True, stroke=False)

        # Starburst serrated outer seal ring
        seal_points = 28
        outer_r = 36
        inner_r = 32
        star_path = c.beginPath()
        for i in range(seal_points * 2):
            angle = i * math.pi / seal_points
            r = outer_r if i % 2 == 0 else inner_r
            px = seal_cx + r * math.cos(angle)
            py = seal_cy + r * math.sin(angle)
            if i == 0:
                star_path.moveTo(px, py)
            else:
                star_path.lineTo(px, py)
        star_path.close()
        c.setFillColor(gold_primary)
        c.drawPath(star_path, fill=True, stroke=False)

        c.setFillColor(navy_dark)
        c.circle(seal_cx, seal_cy, 27, fill=True, stroke=False)
        c.setStrokeColor(gold_light)
        c.setLineWidth(1)
        c.circle(seal_cx, seal_cy, 24, fill=False, stroke=True)

        c.setFillColor(gold_light)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(seal_cx, seal_cy + 9, "RAGNIFY VERIFIED")
        c.setFont("Times-Bold", 9)
        c.setFillColor(colors.HexColor('#FFFFFF'))
        c.drawCentredString(seal_cx, seal_cy - 2, "OFFICIAL")
        c.setFillColor(gold_primary)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(seal_cx, seal_cy - 11, "SEAL • 2026")

        # 11. Bottom Registry Footer Bar
        c.setFillColor(muted_text)
        c.setFont("Helvetica", 7.5)
        c.drawString(52, 46, f"Certificate ID: CERT-{clean_id}   |   Candidate ID: {clean_id}")
        c.drawRightString(width - 52, 46, f"Date of Issuance: {date.today().strftime('%B %d, %Y')}   |   Status: VERIFIED & AUTHENTIC")

        c.save()
    except Exception as e:
        print(f"Error generating certificate PDF: {e}")

    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={pdf_filename}"})

    raise HTTPException(status_code=404, detail="Certificate PDF could not be generated.")


