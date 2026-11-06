import os
import re
import json
from uuid import uuid4
from datetime import date, datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from groq import Groq

from models import Meeting

load_dotenv()

_groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()
client = None
if _groq_api_key:
    try:
        client = Groq(api_key=_groq_api_key)
    except Exception:
        client = None

def get_groq_client():
    global client
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not key:
        raise HTTPException(
            status_code=400,
            detail="GROQ_API_KEY is not configured in Enterprise_AI_Backend/.env. Please configure your Groq Cloud API key to transcribe and analyze audio."
        )
    if client is None:
        try:
            client = Groq(api_key=key)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize Groq client: {e}")
    return client

AUDIO_UPLOAD_DIR = os.path.join("uploads", "audio")
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".wav"}


def generate_next_meeting_id(db: Session) -> str:
    """Generate next unique meeting ID in MTG011 format."""
    try:
        result = db.execute(text("SELECT meeting_id FROM meetings WHERE meeting_id LIKE 'MTG%'"))
        ids = [row[0] for row in result.fetchall()]
        
        max_num = 0
        for m_id in ids:
            match = re.search(r'MTG(\d+)', m_id, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        
        next_num = max_num + 1
        return f"MTG{next_num:03d}"
    except Exception:
        return f"MTG{uuid4().hex[:6].upper()}"


def parse_meeting_date(date_str: str) -> date:
    """Parse date string into date object or fallback to today."""
    if not date_str or date_str.lower() in {"not specified", "unknown", "n/a"}:
        return date.today()
    
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            pass
            
    return date.today()


def format_decisions(raw_decisions) -> str:
    """Format decisions list or string into clean, readable bullet points."""
    if isinstance(raw_decisions, list):
        items = []
        for d in raw_decisions:
            if isinstance(d, dict):
                items.append(f"• {d.get('decision') or d.get('title') or str(d)}")
            else:
                items.append(f"• {str(d)}")
        return "\n".join(items) if items else "Decisions documented in sprint tracker"
    return str(raw_decisions or "Decisions documented in sprint tracker")


def format_action_items(raw_actions) -> str:
    """Format action items list or string into clean, readable bullet points with owners."""
    if isinstance(raw_actions, list):
        items = []
        for a in raw_actions:
            if isinstance(a, dict):
                task = a.get("task") or a.get("action") or a.get("title") or "Task"
                owner = a.get("owner") or a.get("assignee") or "Team"
                due = a.get("due_date") or a.get("deadline")
                due_str = f" [Due: {due}]" if due else ""
                items.append(f"• {task} — Owner: {owner}{due_str}")
            else:
                items.append(f"• {str(a)}")
        return "\n".join(items) if items else "Action items assigned to respective module owners"
    return str(raw_actions or "Action items assigned to respective module owners")


def process_meeting_audio(file_bytes: bytes, original_filename: str, db: Session) -> dict:
    """
    Complete Meeting Audio Processing Pipeline:
    1. Validate audio extension & non-empty content
    2. Save audio file to uploads/audio/
    3. Transcribe audio using Groq Whisper (whisper-large-v3)
    4. Generate structured summary JSON using Groq LLM (openai/gpt-oss-120b)
    5. Save meeting record to PostgreSQL
    6. Return response object with meeting details + key_points
    """
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Only .mp3 and .wav audio files are accepted."
        )

    if not file_bytes or len(file_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded audio file is empty."
        )

    # Save audio file to disk
    sanitized_name = re.sub(r'[^\w\.-]', '_', original_filename)
    unique_audio_filename = f"meeting_{uuid4().hex[:8]}_{sanitized_name}"
    audio_filepath = os.path.join(AUDIO_UPLOAD_DIR, unique_audio_filename)

    try:
        with open(audio_filepath, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save audio file to disk: {str(e)}"
        )

    # 1. Transcribe audio using Groq Whisper (whisper-large-v3) with multilingual prompt
    prompt_context = (
        "Multilingual corporate meeting, Indian team discussion, English, Hindi, Hinglish, "
        "Tamil, Telugu, Kannada, Bengali, Marathi, Gujarati, Punjabi, Malayalam, Urdu. "
        "Audio may contain sprint deliverables, technical architecture, speeches, or background music/songs."
    )

    gclient = get_groq_client()

    try:
        with open(audio_filepath, "rb") as audio_file:
            audio_bytes_read = audio_file.read()

        transcription = gclient.audio.transcriptions.create(
            file=(unique_audio_filename, audio_bytes_read),
            model="whisper-large-v3",
            response_format="verbose_json",
            prompt=prompt_context
        )
        
        raw_transcript = str(getattr(transcription, "text", "")).strip()
        if not raw_transcript:
            raise ValueError("Whisper transcription returned empty text.")
            
        whisper_detected_lang = str(getattr(transcription, "language", "english")).lower()

    except Exception as e:
        if os.path.exists(audio_filepath):
            os.remove(audio_filepath)
        raise HTTPException(
            status_code=500,
            detail=f"Audio transcription failed: {str(e)}"
        )

    # 1.1 Direct English Audio Translation via Whisper (if non-English or code-switched)
    english_translated_speech = ""
    is_non_english = whisper_detected_lang != "english" or any(ord(c) > 127 for c in raw_transcript)
    
    if is_non_english:
        try:
            translation_res = gclient.audio.translations.create(
                file=(unique_audio_filename, audio_bytes_read),
                model="whisper-large-v3",
                prompt="Translate Indian multilingual speech, Hindi, Hinglish, regional language or audio lyrics into clear English."
            )
            english_translated_speech = str(getattr(translation_res, "text", "")).strip()
        except Exception as trans_err:
            print(f"Direct Whisper translation notice: {trans_err}")

    # 2. Generate structured multilingual intelligence using Groq LLM (openai/gpt-oss-120b)
    prompt = f"""You are RAGNIFY's Enterprise Universal Multilingual Meeting & Audio Intelligence AI.
In Indian and global enterprises, audio recordings frequently contain code-switching (Hinglish: Hindi + English), pure Hindi, Tamil, Telugu, Marathi, Bengali, or other Indian & global languages, as well as business presentations, general speech, and musical MP3 audio/songs.

YOUR MANDATE:
1. DETECT & UNDERSTAND ANY LANGUAGE:
   - Accurately identify the language(s) spoken (e.g. "Hindi & English (Hinglish)", "Hindi (हिन्दी)", "English (Indian/Corporate)", "Tamil (தமிழ்)", "Telugu", "Marathi", "Multilingual Indian").
   - Whisper auto-detected language code: "{whisper_detected_lang}".

2. DELIVER 100% OF THE VIEW INTELLIGENCE IN CLEAR, EXECUTIVE-GRADE ENGLISH:
   - Every single output field (meeting_title, agenda, decisions, action_items, summary, key_points, english_transcript) MUST be written in fluent, professional, articulate corporate ENGLISH.
   - If the audio is in Hindi, Hinglish, or any regional/foreign language, translate and synthesize all concepts, decisions, and takeaways into executive English.

3. ROBUST INTELLIGENCE FOR BOTH MEETINGS AND AUDIO/MUSIC INPUTS:
   - If it is a business meeting or sprint discussion: Synthesize clear agenda, decisions, action items with assigned owners, and roadmap milestones in English.
   - If it is an MP3 music track, song, creative audio, or speech: Analyze the theme, lyrics, message, artistic narrative, and synthesize an insightful executive briefing with key takeaways and follow-up implications. DO NOT leave fields as 'Not specified' if context can be derived.

Adhere strictly to this JSON schema:
{{
  "meeting_title": "Concise, professional title in English",
  "detected_language": "Detected language (e.g., Hinglish (Hindi + English) / Hindi / English / Multilingual)",
  "audio_type": "Classification (e.g., Sprint Alignment / Technical Review / Multilingual Strategy / Audio Presentation)",
  "meeting_date": "YYYY-MM-DD or today's date",
  "duration": "Estimated duration (e.g., 45 mins / 5 mins)",
  "organizer": "Meeting Organizer, Primary Speaker, or Lead",
  "participants": "List of attendees, speakers, or departments involved",
  "agenda": "Core agenda and topics discussed (in English)",
  "decisions": "Key decisions, conclusions, or consensus points reached (in English)",
  "action_items": "Assigned action items with tasks, owners, and next milestones (in English)",
  "summary": "Comprehensive 3-5 sentence Executive Summary highlighting key discussions, technical decisions, and strategic outcomes (in English)",
  "key_points": [
    "Key takeaway point 1 in English",
    "Key takeaway point 2 in English",
    "Key takeaway point 3 in English"
  ],
  "english_transcript": "Complete transcript translated and polished into English"
}}

Audio Data:
[WHISPER DETECTED LANGUAGE]: {whisper_detected_lang}
[ORIGINAL AUDIO TRANSCRIPT]:
{raw_transcript}

[TRANSLATED SPEECH DIGEST]:
{english_translated_speech or "Direct transcription above"}

Return ONLY the raw valid JSON object:"""

    try:
        completion = gclient.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        response_content = completion.choices[0].message.content.strip()

        # Strip markdown ```json fences if returned by LLM
        if response_content.startswith("```"):
            response_content = re.sub(r"^```(?:json)?\n?", "", response_content)
            response_content = re.sub(r"\n?```$", "", response_content)
            response_content = response_content.strip()

        summary_json = json.loads(response_content)

    except Exception as e:
        if os.path.exists(audio_filepath):
            os.remove(audio_filepath)
        raise HTTPException(
            status_code=500,
            detail=f"AI meeting summarization failed: {str(e)}"
        )

    # 3. Save to PostgreSQL database
    try:
        next_meeting_id = generate_next_meeting_id(db)
        raw_date_str = str(summary_json.get("meeting_date", "Not specified"))
        parsed_date = parse_meeting_date(raw_date_str)

        detected_language = str(summary_json.get("detected_language", "Hindi & English (Hinglish)"))
        audio_type = str(summary_json.get("audio_type", "Multilingual Corporate Meeting"))
        english_transcript = str(summary_json.get("english_transcript", english_translated_speech or raw_transcript))

        # Format dual-view transcript containing both English Digest & Original Spoken Audio
        formatted_transcript = (
            f"🌐 DETECTED AUDIO LANGUAGE: {detected_language} | TYPE: {audio_type}\n"
            f"═════════════════════════════════════════════════════════════════════\n"
            f"📖 ENGLISH TRANSLATED TRANSCRIPT DIGEST:\n"
            f"{english_transcript}\n\n"
            f"═════════════════════════════════════════════════════════════════════\n"
            f"🎙️ ORIGINAL AUDIO RECORDING TRANSCRIPT ({detected_language}):\n"
            f"{raw_transcript}"
        )

        decisions_str = format_decisions(summary_json.get("decisions"))
        action_items_str = format_action_items(summary_json.get("action_items"))

        meeting_record = Meeting(
            meeting_id=next_meeting_id,
            meeting_title=str(summary_json.get("meeting_title", "Meeting Summary")),
            meeting_date=parsed_date,
            duration=str(summary_json.get("duration", "45 mins")),
            organizer=str(summary_json.get("organizer", "Team Lead")),
            participants=str(summary_json.get("participants", "Engineering Team")),
            agenda=str(summary_json.get("agenda", "Sprint alignment and feature deliverables")),
            decisions=decisions_str,
            action_items=action_items_str,
            summary=str(summary_json.get("summary", "Executive summary synthesized in professional English.")),
            transcript=formatted_transcript,
            audio_filename=unique_audio_filename
        )

        db.add(meeting_record)
        db.commit()
        db.refresh(meeting_record)

    except Exception as e:
        db.rollback()
        if os.path.exists(audio_filepath):
            os.remove(audio_filepath)
        raise HTTPException(
            status_code=500,
            detail=f"Database insertion failed: {str(e)}"
        )

    # 4. Construct API response with full multilingual intelligence
    key_points = summary_json.get("key_points", [])
    if isinstance(key_points, str):
        key_points = [key_points]

    return {
        "meeting_id": meeting_record.meeting_id,
        "meeting_title": meeting_record.meeting_title,
        "meeting_date": str(meeting_record.meeting_date),
        "duration": meeting_record.duration,
        "organizer": meeting_record.organizer,
        "participants": meeting_record.participants,
        "agenda": meeting_record.agenda,
        "decisions": meeting_record.decisions,
        "action_items": meeting_record.action_items,
        "summary": meeting_record.summary,
        "key_points": key_points,
        "transcript": meeting_record.transcript,
        "english_transcript": english_transcript,
        "original_transcript": raw_transcript,
        "detected_language": detected_language,
        "audio_type": audio_type,
        "audio_filename": meeting_record.audio_filename
    }
