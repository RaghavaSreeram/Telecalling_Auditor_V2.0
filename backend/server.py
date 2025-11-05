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

# Pydantic Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    role: str = "admin"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

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
        full_name=user_data.full_name
    )
    
    user_dict = user.model_dump()
    user_dict["created_at"] = user_dict["created_at"].isoformat()
    user_dict["password_hash"] = hash_password(user_data.password)
    
    await db.users.insert_one(user_dict)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc or not verify_password(credentials.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user = User(**{k: v for k, v in user_doc.items() if k != "password_hash"})
    
    access_token = create_access_token(
        data={"sub": user.id},
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
    audits = await db.audio_audits.find({}, {"_id": 0}).sort("upload_date", -1).to_list(1000)
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

# Manager Dashboard Analytics Routes
@api_router.get("/manager/analytics/overview")
async def get_manager_overview(current_user: User = Depends(get_current_user)):
    from analytics import get_overall_analytics
    return await get_overall_analytics(db)

@api_router.get("/manager/analytics/agents")
async def get_agent_performance(agent_id: str = None, current_user: User = Depends(get_current_user)):
    from analytics import calculate_agent_performance
    return await calculate_agent_performance(db, agent_id)

@api_router.get("/manager/analytics/sentiment")
async def get_sentiment_analysis(current_user: User = Depends(get_current_user)):
    from analytics import get_sentiment_trends
    return await get_sentiment_trends(db)

@api_router.get("/manager/analytics/leadership-insights")
async def get_leadership_dashboard(current_user: User = Depends(get_current_user)):
    from analytics import get_leadership_insights
    return await get_leadership_insights(db)

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
