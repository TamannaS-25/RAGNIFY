# 🚀 RAGNIFY — Enterprise AI & HR Onboarding Intelligence Platform

[![React](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Groq](https://img.shields.io/badge/LLM%20Inference-Groq%20Cloud-F05032)](https://groq.com/)
[![ChromaDB](https://img.shields.io/badge/Vector%20Store-ChromaDB-FF6F00)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/TamannaS-25/RAGNIFY/actions/workflows/ci.yml/badge.svg)](https://github.com/TamannaS-25/RAGNIFY/actions)

> **RAGNIFY** is an all-in-one Enterprise AI ecosystem that streamlines corporate onboarding, recruitment screening, organizational policy intelligence, and executive meeting analytics. Powered by Retrieval-Augmented Generation (RAG), Automated ATS Resume Scoring, and Multilingual Audio Intelligence.

---

## 📌 Problem Statement

Traditional corporate recruitment, onboarding, and HR management suffer from:
1. **Manual Resume Screening Bottlenecks:** HR teams spend hours manually matching candidate resumes against department competencies.
2. **Disconnected Onboarding Portals:** Fragmented document collection and manual role assignment without real-time ATS feedback.
3. **Static Company Policy Lookups:** Employees struggle to find exact guidelines across 100+ page policy PDFs, leading to repetitive HR queries.
4. **Multilingual Meeting Friction:** In multilingual teams (especially in India, where discussions mix English, Hindi, and regional dialects), documenting action items and key decisions is error-prone and time-consuming.

**RAGNIFY solves all four challenges inside a unified, enterprise-grade AI architecture.**

---

## ✨ Core Pillars & Features

### 1. 🎯 Automated ATS Resume Scanner & Competency Matching
- **Automated PDF Parsing:** Ingests candidate resumes using `pypdf` and extracts text content instantly.
- **Department Competency Matrix:** Pre-configured with 5–6 core industry competencies across **8 enterprise departments** (Engineering, AI & Data Science, Product & Design, Infrastructure, Finance, Sales & Marketing, HR, QA & Testing).
- **Match Scoring Engine (0–100%):** Calculates keyword match percentage, flags missing skills, and renders color-coded indicators (High Match $\ge$ 70%, Moderate 50–69%, Low Match < 50%).
- **Automated Candidate Cleanup:** Rejected applications can be automatically deleted along with associated storage files.

### 2. 🏢 Interactive Department Slicer & Dual Onboarding Portals
- **Targeted Application Flows:** Separate onboarding journeys for **Interns** (3-document compliance) and **Full-time Employees** (5-document compliance).
- **Interactive Department Slicer:** Dynamic 8-department slicer that instantly filters available positions based on the selected domain.
- **Real-Time ATS Keyword Advisory:** Displays target competencies directly beneath the slicer so candidates understand how their resume will be screened.

### 3. 💬 Socratic RAG Policy Assistant (Two-Way Interactive Copilot)
- **Teacher-Like Two-Way Conversation:** Clarifies ambiguous questions instead of giving generic answers.
- **Clickable Category Pills:** Offers clickable policy category buttons (e.g., Annual Leave, Health Insurance, Code of Conduct) to guide employees to the exact clause.
- **Accurate & Grounded Retrieval:** Powered by ChromaDB vector store and Groq LLM inference, ensuring zero hallucinations.
- **Intelligent Fallbacks:** Gracefully alerts users if a requested policy does not exist and suggests related corporate documentation.

### 4. 🎙️ Multilingual Meeting Intelligence
- **Universal Audio Processing:** Accepts audio recordings (`.mp3`, `.wav`, `.m4a`) in any language or dialect (Hindi, English, Hinglish, regional languages).
- **Language Detection & Translation:** Automatically detects spoken languages and transcribes discussions into clean, structured **English Executive Intelligence**.
- **Executive Deliverables:** Generates executive summaries, key decisions made, assigned action items, and participant sentiment analysis.

### 5. 🔐 Role-Based Access Control (RBAC) & Frictionless 2FA
- **6 Supported Enterprise Roles:** HR, Employee, Intern, Manager, Finance, and IT Admin.
- **Frictionless Two-Factor Authentication:** Automatically pre-fills the registered phone number for the selected role with one-click on-screen OTP verification.

---

## 🏛️ System Architecture

```text
                     +---------------------------------------+
                     |         RAGNIFY React Frontend        |
                     |  (Vite + React 18 + Modular CSS)      |
                     +-------------------+-------------------+
                                         |
                       REST API Calls / FormData Uploads
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        Enterprise FastAPI Backend (Python)                        |
+---------------------+---------------------+-------------------+-------------------+
|  Auth & 2FA Router  |  Onboarding Router  |  RAG / AI Router  |  Meeting Router   |
|  - Role Resolution  |  - Dept Slicer API  |  - Socratic Agent |  - Audio Ingest   |
|  - OTP Generator    |  - ATS Resume Scan  |  - Groq LLM API   |  - Lang Detection |
|  - Session Tokens   |  - Auto-Cleanup     |  - ChromaDB RAG   |  - Exec Summaries |
+---------------------+---------------------+-------------------+-------------------+
          |                      |                    |                   |
          v                      v                    v                   v
   +--------------+      +---------------+     +---------------+   +---------------+
   | SQLite / DB  |      |  PDF Resumes  |     | Chroma Vector |   | Groq Whisper  |
   | User Records |      |  & Documents  |     |  Embeddings   |   | & LLaMA-3 LLM |
   +--------------+      +---------------+     +---------------+   +---------------+
```

---

## 📊 Department Competency Matrix (ATS Scanner)

| Department | Key Competencies Scanned |
| :--- | :--- |
| **Engineering** | `Python`, `JavaScript`, `React`, `FastAPI`, `SQL`, `Git` |
| **AI & Data Science** | `Python`, `Machine Learning`, `PyTorch`, `Deep Learning`, `NLP`, `Pandas` |
| **Product & Design** | `Figma`, `UI/UX`, `Wireframing`, `User Research`, `Prototyping`, `Design System` |
| **Infrastructure / Cloud** | `Docker`, `Kubernetes`, `AWS`, `CI/CD`, `Linux`, `Terraform` |
| **Finance & Accounts** | `Accounting`, `Financial Modeling`, `Budgeting`, `Auditing`, `Taxation`, `Excel` |
| **Sales & Marketing** | `SEO`, `Lead Generation`, `Digital Marketing`, `CRM`, `Content Strategy`, `Campaign Management` |
| **HR & People Ops** | `Talent Acquisition`, `Onboarding`, `Payroll`, `Compliance`, `Employee Relations`, `HRIS` |
| **QA & Testing** | `Test Automation`, `Selenium`, `API Testing`, `Bug Tracking`, `Manual Testing`, `Test Cases` |

---

## 🛠️ Technology Stack

| Domain | Technologies Used |
| :--- | :--- |
| **Frontend** | React 18, Vite, React Router DOM, Lucide Icons, React Icons |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic, SQLAlchemy |
| **AI / NLP** | Groq Cloud API (`llama-3.3-70b-versatile`), ChromaDB, Sentence Transformers |
| **Audio & Speech** | Groq Whisper Large v3 / Multilingual Speech Recognition |
| **Document Processing**| `pypdf`, `python-multipart` |
| **Database** | SQLite (Development) / PostgreSQL (Production) |

---

## 📂 Project Directory Structure

```text
ragnify-enterprise-ai/
├── Enterprise_AI_Backend/        # FastAPI Application
│   ├── main.py                   # API Gateway & Middleware
│   ├── database.py               # Database Connection & Engine
│   ├── models.py                 # SQLAlchemy ORM Models
│   ├── routers/
│   │   ├── auth.py               # 2FA Login & Role Management
│   │   ├── onboarding.py         # Onboarding & ATS Resume Scanner
│   │   ├── meeting_summary.py    # Multilingual Meeting Intelligence
│   │   └── rag_copilot.py        # Conversational Policy Assistant
│   ├── uploads/                  # Uploaded Documents & PDF Resumes
│   └── requirements.txt          # Python Dependencies
│
├── Ragnify_Frontend/             # React Application
│   ├── src/
│   │   ├── api/                  # Axios Service Modules
│   │   ├── components/           # Reusable UI & Navigation Elements
│   │   ├── pages/
│   │   │   ├── auth/             # Login, Intern & Employee Applications
│   │   │   ├── hr/               # HR Applications & ATS Review Portal
│   │   │   ├── assistant/        # Socratic RAG Policy Copilot
│   │   │   └── meetings/         # Meeting Summary & Intelligence
│   │   ├── styles/               # CSS Design System
│   │   ├── App.jsx               # Client Routing
│   │   └── main.jsx              # Entry Point
│   ├── package.json
│   └── vite.config.js
│
└── README.md                     # Documentation
```

---

## ⚡ Getting Started & Installation

### Prerequisites
- **Node.js** (v18.x or higher)
- **Python** (v3.10 or higher)
- **Groq Cloud API Key** ([Get one here](https://console.groq.com/))

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/TamannaS-25/RAGNIFY.git
cd RAGNIFY
```

---

### Step 2: Backend Setup
```bash
cd Enterprise_AI_Backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file (.env)
echo GROQ_API_KEY=your_groq_api_key_here >> .env

# Run FastAPI backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Backend API will be live at: `http://localhost:8000` (Swagger docs: `http://localhost:8000/docs`)

---

### Step 3: Frontend Setup
Open a new terminal window:
```bash
cd Ragnify_Frontend

# Install NPM dependencies
npm install

# Start Vite development server
npm run dev
```
Frontend portal will be live at: `http://localhost:5173`

---

## 🔑 Default Demo Roles (2FA Enabled)

| Role | Mobile Number | Purpose |
| :--- | :--- | :--- |
| **HR Manager** | `9876543210` | Full candidate screening, ATS scores & auto-cleanup |
| **Employee** | `9876543211` | Self-service onboarding, RAG policy assistant |
| **Intern** | `9876543212` | Academic onboarding portal & project view |
| **Manager** | `9876543213` | Multilingual meeting intelligence & team insights |
| **Finance** | `9876543214` | Payroll & compliance verification |
| **IT Admin** | `9876543215` | System telemetry & security controls |

---

## 👥 Authors

| Author Name | Institution | Department |
| :--- | :--- | :--- |
| **Shreya Bawankule** | Priyadarshini College of Engineering, Nagpur | Robotics & Artificial Intelligence |
| **Shruti Ghumgaonkar** | Priyadarshini College of Engineering, Nagpur | Robotics & Artificial Intelligence |
| **Mansi Faldu** | Priyadarshini College of Engineering, Nagpur | Robotics & Artificial Intelligence |
| **Tammana Sahare** | Priyadarshini College of Engineering, Nagpur | Robotics & Artificial Intelligence |
| **Vishal Thakre** | Priyadarshini College of Engineering, Nagpur | Robotics & Artificial Intelligence |

---


