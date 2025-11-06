from fastapi import FastAPI, APIRouter, HTTPException, Depends, File, UploadFile, Form, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt
import requests
import json
from openai import OpenAI
from rbac import Role, Permission, has_permission, require_role, get_role_permissions
from audit_service import AuditService
from transcript_service import TranscriptService
from crm_service import CRMService
from models import (
    AuditAssignment, AuditResponse, CallReference, 
    AuditFormSchema, RetentionPolicy, DashboardStats
)
from crm_models import CRMRecord, CRMHealthStats, SyncTrendData

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# API Keys
ASSEMBLYAI_API_KEY = os.environ.get('ASSEMBLYAI_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Initialize services
audit_service = None  # Will be initialized after db connection
crm_service = None  # Will be initialized after db connection

# Pydantic Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    role: str = "auditor"  # auditor, manager, admin
    team_id: Optional[str] = None
    status: str = "active"  # active, inactive, suspended
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "auditor"
    team_id: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Script(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    expected_outcomes: List[str]
    key_points: List[str]
    category: str = "general"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    usage_count: int = 0
    avg_score: float = 0.0

class ScriptCreate(BaseModel):
    title: str
    content: str
    expected_outcomes: List[str]
    key_points: List[str]
    category: str = "general"

class ScriptUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    expected_outcomes: Optional[List[str]] = None
    key_points: Optional[List[str]] = None
    category: Optional[str] = None

class AudioAudit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_number: str
    customer_number: str
    script_id: str
    audio_filename: str
    audio_url: Optional[str] = None
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    call_date: datetime
    call_duration: Optional[int] = None
    status: str = "pending"  # pending, processing, completed, failed
    transcript: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    overall_score: Optional[float] = None
    processed_at: Optional[datetime] = None

class AudioAuditCreate(BaseModel):
    agent_number: str
    customer_number: str
    script_id: str
    call_date: str

class AuditResult(BaseModel):
    audit_id: str
    overall_score: float
    script_adherence_score: float
    communication_score: float
    outcome_achieved: bool
    lead_status: str
    transcript: str
    detailed_analysis: Dict[str, Any]

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

# AssemblyAI transcription
async def transcribe_audio_assemblyai(audio_url: str) -> dict:
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    
    # Upload file
    upload_response = requests.post(
        "https://api.assemblyai.com/v2/upload",
        headers=headers,
        data=open(audio_url, "rb") if os.path.exists(audio_url) else None
    )
    
    if upload_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to upload audio to AssemblyAI")
    
    audio_upload_url = upload_response.json()["upload_url"]
    
    # Request transcription
    transcript_request = {
        "audio_url": audio_upload_url,
        "speaker_labels": True
    }
    
    transcript_response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json=transcript_request,
        headers=headers
    )
    
    transcript_id = transcript_response.json()["id"]
    
    # Poll for completion
    import time
    while True:
        transcript_result = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers
        )
        
        result = transcript_result.json()
        
        if result["status"] == "completed":
            return result
        elif result["status"] == "error":
            raise HTTPException(status_code=500, detail="Transcription failed")
        
        time.sleep(3)

# OpenAI analysis with comprehensive system role
async def analyze_transcript(transcript: str, script: Script, agent_number: str, customer_number: str, call_date: datetime) -> dict:
    system_prompt = """SYSTEM ROLE:
You are an AI Quality Analyst for Radiance Realty's Telecaller Audit platform. 
Your job is to evaluate each telecaller call recording after transcription and provide 
structured JSON output with detailed performance insights for the agent, team, and management.

TASK:
Analyze the transcribed conversation between the agent and customer to extract 
key operational metrics, evaluate performance quality, and generate management-level insights.

PRIMARY EVALUATION METRICS (Per Call)
For each call, extract or compute the following fields:
- agent_id: unique identifier of the telecaller
- customer_id: CRM or lead ID
- call_start_time: timestamp of the call start
- call_duration_seconds: estimated duration based on conversation length
- script_followed: true/false – whether mandatory script keywords were mentioned
- lead_qualified: true/false – whether agent captured intent, budget, location, and timeline
- site_visit_confirmed: true/false – whether a site visit or brochure confirmation occurred
- sentiment: "positive", "neutral", or "negative" based on customer tone and interest
- remarks: short feedback for the agent
- script_adherence_score: 0-100 score for following the script
- communication_score: 0-100 score for communication quality
- overall_score: 0-100 overall performance score

PERFORMANCE METRICS (Aggregated)
- script_adherence_rate: percentage of script followed
- lead_qualification_rate: quality of lead qualification
- site_visit_conversion_rate: success in closing for site visit
- sentiment_positive_rate: positive customer sentiment percentage

OUTPUT FORMAT (Strict JSON)
Return JSON exactly in this format - no explanations, markdown, or additional text:

{
  "agent_id": "string",
  "customer_id": "string",
  "call_start_time": "ISO timestamp",
  "call_duration_seconds": number,
  "script_followed": boolean,
  "lead_qualified": boolean,
  "site_visit_confirmed": boolean,
  "sentiment": "positive/neutral/negative",
  "remarks": "string",
  "overall_score": number,
  "script_adherence_score": number,
  "communication_score": number,
  "outcome_achieved": boolean,
  "lead_status": "qualified/site_visit_scheduled/follow_up_required/not_interested",
  "script_adherence_details": {
    "followed_points": ["array of strings"],
    "missed_points": ["array of strings"],
    "deviations": "string"
  },
  "communication_analysis": {
    "tone": "professional/casual/aggressive/friendly",
    "clarity": number,
    "listening_skills": number,
    "objection_handling": number
  },
  "strengths": ["array of strings"],
  "areas_for_improvement": ["array of strings"],
  "summary": "string",
  "performance_metrics": {
    "script_adherence_rate": number,
    "lead_qualification_rate": number,
    "site_visit_conversion_rate": number,
    "sentiment_positive_rate": number
  }
}

EVALUATION STYLE:
- Be precise, data-driven, and professional
- Only output valid JSON
- Base all metrics on the actual conversation"""

    user_prompt = f"""
**Agent ID:** {agent_number}
**Customer ID:** {customer_number}
**Call Date:** {call_date.isoformat()}

**Telecalling Script:**
{script.content}

**Expected Outcomes:**
{', '.join(script.expected_outcomes)}

**Key Points to Cover:**
{', '.join(script.key_points)}

**Actual Conversation Transcript:**
{transcript}

Analyze this call and provide the structured JSON output as specified in the system role.
"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        analysis = json.loads(response.choices[0].message.content)
        return analysis
    except Exception as e:
        logging.error(f"OpenAI analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Background task for processing audio
async def process_audio_audit(audit_id: str, audio_path: str, script: Script, agent_number: str, customer_number: str, call_date: datetime):
    try:
        # Update status to processing
        await db.audio_audits.update_one(
            {"id": audit_id},
            {"$set": {"status": "processing"}}
        )
        
        # Transcribe audio
        transcription_result = await transcribe_audio_assemblyai(audio_path)
        transcript = transcription_result.get("text", "")
        
        # Analyze transcript with enhanced system prompt
        analysis = await analyze_transcript(transcript, script, agent_number, customer_number, call_date)
        
        # Update audit record
        update_data = {
            "transcript": transcript,
            "analysis": analysis,
            "overall_score": analysis.get("overall_score", 0),
            "status": "completed",
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.audio_audits.update_one(
            {"id": audit_id},
            {"$set": update_data}
        )
        
        # Update script analytics
        await db.scripts.update_one(
            {"id": script.id},
            {
                "$inc": {"usage_count": 1},
                "$set": {
                    "avg_score": analysis.get("overall_score", 0)  # Simplified, should calculate average
                }
            }
        )
        
    except Exception as e:
        logging.error(f"Processing error: {str(e)}")
        await db.audio_audits.update_one(
            {"id": audit_id},
            {"$set": {"status": "failed"}}
        )

# Routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        team_id=user_data.team_id
    )
    
    user_dict = user.model_dump()
    user_dict["created_at"] = user_dict["created_at"].isoformat()
    user_dict["password_hash"] = hash_password(user_data.password)
    
    await db.users.insert_one(user_dict)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc or not verify_password(credentials.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user is active
    if user_doc.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account is inactive or suspended")
    
    user = User(**{k: v for k, v in user_doc.items() if k != "password_hash"})
    
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Script routes
@api_router.post("/scripts", response_model=Script)
async def create_script(script_data: ScriptCreate, current_user: User = Depends(get_current_user)):
    script = Script(**script_data.model_dump())
    script_dict = script.model_dump()
    script_dict["created_at"] = script_dict["created_at"].isoformat()
    script_dict["updated_at"] = script_dict["updated_at"].isoformat()
    
    await db.scripts.insert_one(script_dict)
    return script

@api_router.get("/scripts", response_model=List[Script])
async def get_scripts(current_user: User = Depends(get_current_user)):
    """All authenticated users can view scripts"""
    scripts = await db.scripts.find({}, {"_id": 0}).to_list(1000)
    for script in scripts:
        if isinstance(script.get("created_at"), str):
            script["created_at"] = datetime.fromisoformat(script["created_at"])
        if isinstance(script.get("updated_at"), str):
            script["updated_at"] = datetime.fromisoformat(script["updated_at"])
    return scripts

@api_router.get("/scripts/{script_id}", response_model=Script)
async def get_script(script_id: str, current_user: User = Depends(get_current_user)):
    script = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    if isinstance(script.get("created_at"), str):
        script["created_at"] = datetime.fromisoformat(script["created_at"])
    if isinstance(script.get("updated_at"), str):
        script["updated_at"] = datetime.fromisoformat(script["updated_at"])
    
    return Script(**script)

@api_router.put("/scripts/{script_id}", response_model=Script)
async def update_script(script_id: str, script_data: ScriptUpdate, current_user: User = Depends(get_current_user)):
    script = await db.scripts.find_one({"id": script_id})
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    update_data = {k: v for k, v in script_data.model_dump(exclude_unset=True).items()}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.scripts.update_one({"id": script_id}, {"$set": update_data})
    
    updated_script = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if isinstance(updated_script.get("created_at"), str):
        updated_script["created_at"] = datetime.fromisoformat(updated_script["created_at"])
    if isinstance(updated_script.get("updated_at"), str):
        updated_script["updated_at"] = datetime.fromisoformat(updated_script["updated_at"])
    
    return Script(**updated_script)

@api_router.delete("/scripts/{script_id}")
async def delete_script(script_id: str, current_user: User = Depends(get_current_user)):
    result = await db.scripts.delete_one({"id": script_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Script not found")
    return {"message": "Script deleted successfully"}

# Audio audit routes
@api_router.post("/audits/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    agent_number: str = Form(...),
    customer_number: str = Form(...),
    script_id: str = Form(...),
    call_date: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    # Verify script exists
    script = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # Save audio file
    upload_dir = Path("/tmp/audio_uploads")
    upload_dir.mkdir(exist_ok=True)
    
    audio_filename = f"{uuid.uuid4()}_{audio_file.filename}"
    audio_path = upload_dir / audio_filename
    
    with open(audio_path, "wb") as f:
        content = await audio_file.read()
        f.write(content)
    
    # Create audit record
    audit = AudioAudit(
        agent_number=agent_number,
        customer_number=customer_number,
        script_id=script_id,
        audio_filename=audio_filename,
        audio_url=str(audio_path),
        call_date=datetime.fromisoformat(call_date.replace("Z", "+00:00"))
    )
    
    audit_dict = audit.model_dump()
    audit_dict["upload_date"] = audit_dict["upload_date"].isoformat()
    audit_dict["call_date"] = audit_dict["call_date"].isoformat()
    
    await db.audio_audits.insert_one(audit_dict)
    
    # Process in background
    script_obj = Script(**script)
    if isinstance(script_obj.created_at, str):
        script_obj.created_at = datetime.fromisoformat(script_obj.created_at)
    if isinstance(script_obj.updated_at, str):
        script_obj.updated_at = datetime.fromisoformat(script_obj.updated_at)
    
    background_tasks.add_task(
        process_audio_audit, 
        audit.id, 
        str(audio_path), 
        script_obj,
        agent_number,
        customer_number,
        audit.call_date
    )
    
    return {"audit_id": audit.id, "message": "Audio uploaded successfully. Processing started."}

@api_router.get("/audits", response_model=List[AudioAudit])
async def get_audits(current_user: User = Depends(get_current_user)):
    """Admin and Manager can view all audits, Auditors see only their assigned ones"""
    if current_user.role in ["admin", "manager"]:
        # Admin and Manager see all audits
        audits = await db.audio_audits.find({}, {"_id": 0}).sort("upload_date", -1).to_list(1000)
    else:
        # Auditors see only their assigned audits
        audits = await db.audio_audits.find(
            {"agent_number": current_user.id},
            {"_id": 0}
        ).sort("upload_date", -1).to_list(1000)
    
    for audit in audits:
        if isinstance(audit.get("upload_date"), str):
            audit["upload_date"] = datetime.fromisoformat(audit["upload_date"])
        if isinstance(audit.get("call_date"), str):
            audit["call_date"] = datetime.fromisoformat(audit["call_date"])
        if isinstance(audit.get("processed_at"), str):
            audit["processed_at"] = datetime.fromisoformat(audit["processed_at"])
    return audits

@api_router.get("/audits/{audit_id}")
async def get_audit(audit_id: str, current_user: User = Depends(get_current_user)):
    audit = await db.audio_audits.find_one({"id": audit_id}, {"_id": 0})
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    # Get script details
    script = None
    if audit.get("script_id"):
        script = await db.scripts.find_one({"id": audit["script_id"]}, {"_id": 0})
    
    if isinstance(audit.get("upload_date"), str):
        audit["upload_date"] = datetime.fromisoformat(audit["upload_date"])
    if isinstance(audit.get("call_date"), str):
        audit["call_date"] = datetime.fromisoformat(audit["call_date"])
    if isinstance(audit.get("processed_at"), str):
        audit["processed_at"] = datetime.fromisoformat(audit["processed_at"])
    
    # Add script details to response
    audit["script_details"] = script
    
    return audit

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    total_audits = await db.audio_audits.count_documents({})
    completed_audits = await db.audio_audits.count_documents({"status": "completed"})
    total_scripts = await db.scripts.count_documents({})
    
    # Get average score
    pipeline = [
        {"$match": {"status": "completed", "overall_score": {"$exists": True}}},
        {"$group": {"_id": None, "avg_score": {"$avg": "$overall_score"}}}
    ]
    avg_result = await db.audio_audits.aggregate(pipeline).to_list(1)
    avg_score = avg_result[0]["avg_score"] if avg_result else 0
    
    return {
        "total_audits": total_audits,
        "completed_audits": completed_audits,
        "pending_audits": total_audits - completed_audits,
        "total_scripts": total_scripts,
        "average_score": round(avg_score, 2)
    }

# RBAC - Role and Permission Routes
@api_router.get("/rbac/roles")
async def get_available_roles(current_user: User = Depends(get_current_user)):
    """Get all available roles and their descriptions"""
    from rbac import ROLE_DESCRIPTIONS
    return ROLE_DESCRIPTIONS

@api_router.get("/rbac/permissions")
async def get_user_permissions(current_user: User = Depends(get_current_user)):
    """Get current user's permissions"""
    user_role = Role(current_user.role)
    permissions = get_role_permissions(user_role)
    return {
        "role": current_user.role,
        "permissions": [p.value for p in permissions]
    }

# Manager Dashboard Analytics Routes (Manager/Admin only)
@api_router.get("/manager/analytics/overview")
async def get_manager_overview(current_user: User = Depends(get_current_user)):
    """Manager/Admin: Get overall analytics overview"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    from analytics import get_overall_analytics
    return await get_overall_analytics(db)

@api_router.get("/manager/analytics/agents")
async def get_agent_performance(agent_id: str = None, current_user: User = Depends(get_current_user)):
    """Manager/Admin: Get agent performance metrics"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    from analytics import calculate_agent_performance
    return await calculate_agent_performance(db, agent_id)

@api_router.get("/manager/analytics/sentiment")
async def get_sentiment_analysis(current_user: User = Depends(get_current_user)):
    """Manager/Admin: Get sentiment analysis"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    from analytics import get_sentiment_trends
    return await get_sentiment_trends(db)

@api_router.get("/manager/analytics/leadership-insights")
async def get_leadership_dashboard(current_user: User = Depends(get_current_user)):
    """Manager/Admin: Get leadership insights and recommendations"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    from analytics import get_leadership_insights
    return await get_leadership_insights(db)

@api_router.get("/analytics/export")
async def export_analytics_report(
    format: str = "csv",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):

@api_router.get("/analytics/export-test")
async def export_analytics_report_test(
    format: str = "csv",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Export analytics report in CSV or PDF format"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    # Get audit data for export
    query = {"status": "completed"}
    
    # Apply date filters if provided
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        if date_filter:
            query["processed_at"] = date_filter
    
    audits = await db.audio_audits.find(query, {"_id": 0}).sort("processed_at", -1).to_list(1000)
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Call ID", "Agent Number", "Customer Number", "Call Date",
            "Overall Score", "Compliance Result", "Script Adherence",
            "Communication Score", "Sentiment", "Lead Status", 
            "Outcome Achieved", "Flags", "Processed At"
        ])
        
        # Write data rows
        for audit in audits:
            analysis = audit.get("analysis", {})
            flags = ", ".join(audit.get("flags", []))
            
            writer.writerow([
                audit.get("id", ""),
                audit.get("agent_number", ""),
                audit.get("customer_number", ""),
                audit.get("call_date", ""),
                audit.get("overall_score", 0),
                audit.get("compliance_result", "N/A"),
                analysis.get("script_adherence_score", 0),
                analysis.get("communication_score", 0),
                analysis.get("sentiment", ""),
                analysis.get("lead_status", ""),
                "Yes" if analysis.get("outcome_achieved") else "No",
                flags,
                audit.get("processed_at", "")
            ])
        
        output.seek(0)
        
        # Return CSV file
        from datetime import datetime
        filename = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif format == "pdf":
        # For PDF, we'll return a simple text-based report for now
        # In production, use a library like ReportLab or WeasyPrint
        from fastapi.responses import PlainTextResponse
        
        report_text = "Audit Analytics Report\n"
        report_text += f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        report_text += f"Total Audits: {len(audits)}\n\n"
        
        if audits:
            total_score = sum(a.get("overall_score", 0) for a in audits)
            avg_score = total_score / len(audits)
            compliance_pass = sum(1 for a in audits if a.get("compliance_result") == "PASS")
            compliance_rate = (compliance_pass / len(audits)) * 100
            
            report_text += f"Average Score: {avg_score:.2f}%\n"
            report_text += f"Compliance Rate: {compliance_rate:.2f}%\n"
            report_text += f"Compliant Audits: {compliance_pass} / {len(audits)}\n\n"
            
            report_text += "Recent Audits:\n"
            report_text += "-" * 80 + "\n"
            
            for audit in audits[:20]:  # Show first 20
                report_text += f"Call ID: {audit.get('id', 'N/A')}\n"
                report_text += f"Agent: {audit.get('agent_number', 'N/A')}\n"
                report_text += f"Score: {audit.get('overall_score', 0):.1f}%\n"
                report_text += f"Compliance: {audit.get('compliance_result', 'N/A')}\n"
                report_text += f"Date: {audit.get('call_date', 'N/A')}\n"
                report_text += "-" * 80 + "\n"
        
        filename = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        return PlainTextResponse(
            report_text,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'pdf'")

# Admin-only routes
@api_router.get("/admin/users")
async def get_all_users(current_user: User = Depends(get_current_user)):
    """Admin only: Get all users in the system"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    for user in users:
        if isinstance(user.get("created_at"), str):
            user["created_at"] = datetime.fromisoformat(user["created_at"])
    return users

@api_router.post("/admin/users")
async def create_user_admin(user_data: UserCreate, current_user: User = Depends(get_current_user)):
    """Admin only: Create a new user"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        team_id=user_data.team_id
    )
    
    user_dict = new_user.model_dump()
    user_dict["created_at"] = user_dict["created_at"].isoformat()
    user_dict["password_hash"] = hash_password(user_data.password)
    
    await db.users.insert_one(user_dict)
    return {"message": "User created successfully", "user": new_user}

@api_router.put("/admin/users/{user_id}")
async def update_user_admin(
    user_id: str, 
    user_data: dict, 
    current_user: User = Depends(get_current_user)
):
    """Admin only: Update user information"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build update data
    update_data = {}
    if "full_name" in user_data:
        update_data["full_name"] = user_data["full_name"]
    if "role" in user_data:
        update_data["role"] = user_data["role"]
    if "team_id" in user_data:
        update_data["team_id"] = user_data["team_id"]
    if "status" in user_data:
        update_data["status"] = user_data["status"]
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    return {"message": "User updated successfully"}

@api_router.delete("/admin/users/{user_id}")
async def delete_user_admin(user_id: str, current_user: User = Depends(get_current_user)):
    """Admin only: Delete a user"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}

@api_router.patch("/admin/users/{user_id}/status")
async def toggle_user_status(
    user_id: str, 
    status_data: dict, 
    current_user: User = Depends(get_current_user)
):
    """Admin only: Toggle user active status"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own status")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"status": status_data.get("status", "active")}}
    )
    return {"message": "User status updated"}

@api_router.get("/admin/stats")
async def get_admin_stats(current_user: User = Depends(get_current_user)):
    """Admin only: Get system-wide statistics"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_users = await db.users.count_documents({})
    total_audits = await db.audio_audits.count_documents({})
    total_scripts = await db.scripts.count_documents({})
    
    return {
        "total_users": total_users,
        "total_audits": total_audits,
        "total_scripts": total_scripts,
        "active_users": await db.users.count_documents({"status": "active"})
    }

# Auditor-specific routes
@api_router.get("/auditor/assigned-audits")
async def get_assigned_audits(current_user: User = Depends(get_current_user)):
    """Auditor only: Get audits assigned to current user"""
    user_role = Role(current_user.role)
    if not has_permission(user_role, Permission.VIEW_ASSIGNED_AUDITS):
        raise HTTPException(status_code=403, detail="Auditor access required")
    
    # Get audits where agent_number matches user's team/assignment
    # For now, filter by agent_number = user.id or team_id
    audits = await db.audio_audits.find(
        {"agent_number": current_user.id},
        {"_id": 0}
    ).sort("upload_date", -1).to_list(100)
    
    for audit in audits:
        if isinstance(audit.get("upload_date"), str):
            audit["upload_date"] = datetime.fromisoformat(audit["upload_date"])
        if isinstance(audit.get("call_date"), str):
            audit["call_date"] = datetime.fromisoformat(audit["call_date"])
    
    return audits

@api_router.get("/auditor/my-metrics")
async def get_auditor_metrics(current_user: User = Depends(get_current_user)):
    """Auditor only: Get personal performance metrics"""
    user_role = Role(current_user.role)
    if not has_permission(user_role, Permission.VIEW_OWN_METRICS):
        raise HTTPException(status_code=403, detail="Auditor access required")
    
    # Calculate metrics for current auditor
    pipeline = [
        {"$match": {"agent_number": current_user.id, "status": "completed"}},
        {
            "$group": {
                "_id": None,
                "total_calls": {"$sum": 1},
                "avg_score": {"$avg": "$overall_score"},
                "site_visits": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.site_visit_confirmed", True]}, 1, 0]}
                },
                "qualified_leads": {
                    "$sum": {"$cond": [{"$eq": ["$analysis.lead_qualified", True]}, 1, 0]}
                }
            }
        }
    ]
    
    results = await db.audio_audits.aggregate(pipeline).to_list(1)
    
    if results:
        stats = results[0]
        return {
            "auditor_id": current_user.id,
            "auditor_name": current_user.full_name,
            "total_calls": stats["total_calls"],
            "avg_score": round(stats["avg_score"], 2),
            "site_visits_confirmed": stats["site_visits"],
            "leads_qualified": stats["qualified_leads"],
            "conversion_rate": round((stats["site_visits"] / stats["total_calls"] * 100), 2) if stats["total_calls"] > 0 else 0
        }
    
    return {
        "auditor_id": current_user.id,
        "auditor_name": current_user.full_name,
        "total_calls": 0,
        "avg_score": 0,
        "site_visits_confirmed": 0,
        "leads_qualified": 0,
        "conversion_rate": 0
    }

# Initialize audit service
audit_service = AuditService(db)

# Audit Queue & Assignment Routes
@api_router.post("/audits/import-call")
async def import_call_reference(call_data: dict, current_user: User = Depends(get_current_user)):
    """Import call reference from CRM/AWS"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin or Manager access required")
    
    call_id = await audit_service.create_call_reference(call_data)
    return {"message": "Call reference imported", "call_id": call_id}

@api_router.get("/call-references")
async def get_call_references(
    limit: int = 10,
    sort: str = "imported_at:desc",
    current_user: User = Depends(get_current_user)
):
    """Get recent call references"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin or Manager access required")
    
    # Parse sort parameter
    sort_field, sort_order = sort.split(":") if ":" in sort else ("imported_at", "desc")
    sort_direction = -1 if sort_order == "desc" else 1
    
    references = await db.call_references.find(
        {}, 
        {"_id": 0}
    ).sort(sort_field, sort_direction).limit(limit).to_list(limit)
    
    return {"references": references}

@api_router.post("/audits/auto-assign")
async def auto_assign_audits(team_id: str = None, current_user: User = Depends(get_current_user)):
    """Auto-assign unassigned calls to auditors"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin or Manager access required")
    
    count = await audit_service.auto_assign_audits(team_id)
    return {"message": f"Assigned {count} calls", "assignments_created": count}

@api_router.post("/audits/manual-assign")
async def manual_assign_audit(
    call_reference_id: str,
    auditor_id: str,
    current_user: User = Depends(get_current_user)
):
    """Manually assign call to specific auditor"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin or Manager access required")
    
    assignment_id = await audit_service.manual_assign(
        call_reference_id, auditor_id, current_user.id
    )
    return {"message": "Call assigned", "assignment_id": assignment_id}

@api_router.get("/audits/pending")
async def get_pending_audits(current_user: User = Depends(get_current_user)):
    """Get pending audits for current auditor"""
    if current_user.role == "auditor":
        audits = await audit_service.get_auditor_queue(current_user.id, "pending")
    else:
        # Manager/Admin see all pending
        audits = await db.audit_assignments.find(
            {"status": "pending"}, {"_id": 0}
        ).to_list(1000)
    
    return audits

@api_router.get("/audits/completed")
async def get_completed_audits(current_user: User = Depends(get_current_user)):
    """Get completed audits"""
    if current_user.role == "auditor":
        audits = await audit_service.get_auditor_queue(current_user.id, "completed")
    else:
        audits = await db.audit_assignments.find(
            {"status": "completed"}, {"_id": 0}
        ).to_list(1000)
    
    return audits

@api_router.get("/audits/my-queue")
async def get_my_audit_queue(current_user: User = Depends(get_current_user)):
    """Get full audit queue for current auditor"""
    if current_user.role != "auditor":
        raise HTTPException(status_code=403, detail="Auditor access only")
    
    audits = await audit_service.get_auditor_queue(current_user.id)
    return audits

# Transcript Routes
@api_router.get("/transcripts/{call_reference_id}")
async def get_transcript(call_reference_id: str, current_user: User = Depends(get_current_user)):
    """Get transcript for a call"""
    # Check if user has access to this call
    call_ref = await db.call_references.find_one({"id": call_reference_id}, {"_id": 0})
    if not call_ref:
        raise HTTPException(status_code=404, detail="Call reference not found")
    
    # Get assignment to verify access
    if current_user.role == "auditor":
        assignment = await db.audit_assignments.find_one({
            "call_reference_id": call_reference_id,
            "auditor_id": current_user.id
        })
        if not assignment:
            raise HTTPException(status_code=403, detail="Not assigned to this audit")
    
    # Fetch transcript
    transcript_segments = await TranscriptService.fetch_transcript(
        call_reference_id, 
        call_ref.get("transcript_url")
    )
    
    return {
        "call_id": call_reference_id,
        "segments": [seg.model_dump() for seg in transcript_segments],
        "formatted_text": TranscriptService.format_transcript_for_display(transcript_segments)
    }

# Audit Form Routes
@api_router.post("/audit-forms")
async def create_audit_form(form_data: dict, current_user: User = Depends(get_current_user)):
    """Create audit form schema"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin or Manager access required")
    
    form_schema = AuditFormSchema(**form_data)
    form_dict = form_schema.model_dump()
    form_dict["created_at"] = form_dict["created_at"].isoformat()
    form_dict["updated_at"] = form_dict["updated_at"].isoformat()
    
    await db.audit_forms.insert_one(form_dict)
    return {"message": "Form created", "form_id": form_schema.id}

@api_router.get("/audit-forms")
async def get_audit_forms(current_user: User = Depends(get_current_user)):
    """Get all active audit forms"""
    forms = await db.audit_forms.find({"is_active": True}, {"_id": 0}).to_list(100)
    return forms

@api_router.get("/audit-forms/{form_id}")
async def get_audit_form(form_id: str, current_user: User = Depends(get_current_user)):
    """Get specific audit form"""
    form = await db.audit_forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form

# Audit Response Routes
@api_router.post("/audits/{assignment_id}/draft")
async def save_audit_draft(
    assignment_id: str,
    draft_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Save audit draft"""
    # Verify assignment belongs to user
    assignment = await db.audit_assignments.find_one({"id": assignment_id})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    if current_user.role == "auditor" and assignment["auditor_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    
    await audit_service.save_audit_draft(
        assignment_id,
        draft_data.get("responses", {}),
        draft_data.get("highlights", [])
    )
    
    return {"message": "Draft saved"}

@api_router.post("/audits/{assignment_id}/submit")
async def submit_audit_response(
    assignment_id: str,
    response_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Submit completed audit"""
    # Verify assignment
    assignment = await db.audit_assignments.find_one({"id": assignment_id})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    if current_user.role == "auditor" and assignment["auditor_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    
    response_id = await audit_service.submit_audit(assignment_id, response_data)
    
    return {"message": "Audit submitted", "response_id": response_id}

@api_router.get("/audits/{assignment_id}/response")
async def get_audit_response(assignment_id: str, current_user: User = Depends(get_current_user)):
    """Get audit response (draft or submitted)"""
    response = await db.audit_responses.find_one({"assignment_id": assignment_id}, {"_id": 0})
    if not response:
        raise HTTPException(status_code=404, detail="No response found")
    
    return response

# Dashboard Routes
@api_router.get("/dashboard/stats")
async def get_enhanced_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get enhanced dashboard statistics"""
    stats = await audit_service.get_dashboard_stats(current_user.id, current_user.role)
    return stats

# Retention Policy Routes
@api_router.post("/admin/retention-policy")
async def create_retention_policy(policy_data: dict, current_user: User = Depends(get_current_user)):
    """Create retention policy"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    policy = RetentionPolicy(**policy_data)
    policy_dict = policy.model_dump()
    policy_dict["created_at"] = policy_dict["created_at"].isoformat()
    policy_dict["updated_at"] = policy_dict["updated_at"].isoformat()
    
    await db.retention_policies.insert_one(policy_dict)
    return {"message": "Retention policy created", "policy_id": policy.id}

@api_router.get("/admin/retention-policies")
async def get_retention_policies(current_user: User = Depends(get_current_user)):
    """Get all retention policies"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin or Manager access required")
    
    policies = await db.retention_policies.find({}, {"_id": 0}).to_list(100)
    return policies

# Initialize CRM service
crm_service = CRMService(db)

# ============================================================================
# CRM Integration Routes
# ============================================================================

@api_router.post("/crm/seed")
async def seed_crm_data(count: int = 50, current_user: User = Depends(get_current_user)):
    """Seed mock CRM data (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await crm_service.seed_mock_data(count)
    return result

@api_router.get("/crm/calls")
async def get_crm_calls(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    campaign: Optional[str] = None,
    transcript_status: Optional[str] = None,
    sync_status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get paginated CRM call records with filters and RBAC"""
    filters = {}
    if search:
        filters["search"] = search
    if campaign:
        filters["campaign_id"] = campaign
    if transcript_status:
        filters["transcript_status"] = transcript_status
    if sync_status:
        filters["sync_status"] = sync_status
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    
    result = await crm_service.get_crm_records(
        user_id=current_user.id,
        user_role=current_user.role,
        filters=filters,
        page=page,
        page_size=page_size
    )
    return result

@api_router.get("/crm/calls/{call_id}")
async def get_crm_call_detail(
    call_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed CRM call record with sync logs"""
    # First get the record by call_id
    record = await db.crm_records.find_one({"call_id": call_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="CRM record not found")
    
    # Use the record's id for detail lookup
    detail = await crm_service.get_crm_record_details(
        record_id=record["id"],
        user_id=current_user.id,
        user_role=current_user.role
    )
    
    if not detail:
        raise HTTPException(status_code=403, detail="Access denied or record not found")
    
    return detail

@api_router.post("/crm/calls/{call_id}/resync")
async def resync_crm_call(
    call_id: str,
    current_user: User = Depends(get_current_user)
):
    """Resync CRM call record (Manager/Admin only)"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    # Get record by call_id
    record = await db.crm_records.find_one({"call_id": call_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="CRM record not found")
    
    try:
        result = await crm_service.resync_crm_record(
            record_id=record["id"],
            user_id=current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resync failed: {str(e)}")

@api_router.post("/crm/calls/{call_id}/validate-mapping")
async def validate_crm_mapping(
    call_id: str,
    current_user: User = Depends(get_current_user)
):
    """Validate and recompute agent mapping (Manager/Admin only)"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    # Get record by call_id
    record = await db.crm_records.find_one({"call_id": call_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="CRM record not found")
    
    try:
        result = await crm_service.validate_mapping(record["id"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@api_router.get("/crm/health")
async def get_crm_health(current_user: User = Depends(get_current_user)):
    """Get CRM integration health statistics"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    stats = await crm_service.get_health_stats()
    return stats

@api_router.get("/crm/health/trends")
async def get_crm_trends(
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Get sync trend data for last N days"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    trends = await crm_service.get_sync_trends(days)
    return {"trends": trends}

@api_router.post("/crm/retry-failed")
async def retry_failed_syncs(current_user: User = Depends(get_current_user)):
    """Retry all failed syncs (Manager/Admin only)"""
    if current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    
    result = await crm_service.retry_failed_syncs()
    return result

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
