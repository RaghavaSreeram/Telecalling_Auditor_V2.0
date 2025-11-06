"""
Enhanced data models for transcript-based auditing system
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from enum import Enum


class AuditStatus(str, Enum):
    """Audit status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FLAGGED = "flagged"
    DRAFT = "draft"


class CallSource(str, Enum):
    """Call data source"""
    CRM = "crm"
    AWS_S3 = "aws_s3"
    MANUAL = "manual"


class TranscriptSegment(BaseModel):
    """Individual transcript segment with speaker and timestamp"""
    speaker: str  # "agent" or "customer"
    text: str
    start_time: float  # seconds from start
    end_time: float
    confidence: Optional[float] = None


class TranscriptHighlight(BaseModel):
    """User-highlighted segment in transcript"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    segment_index: int
    start_char: int
    end_char: int
    text: str
    note: Optional[str] = None
    flag_type: Optional[str] = None  # "positive", "negative", "neutral"
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CallReference(BaseModel):
    """Call reference imported from CRM/AWS"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str  # External CRM call ID
    agent_id: str
    customer_id: Optional[str] = None
    date_time: datetime
    duration_seconds: Optional[int] = None
    campaign_id: Optional[str] = None
    source: CallSource = CallSource.CRM
    transcript_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retention_until: Optional[datetime] = None


class AuditFormField(BaseModel):
    """Dynamic audit form field definition"""
    id: str
    label: str
    type: str  # "number", "checkbox", "text", "select", "rating"
    required: bool = False
    options: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    weight: Optional[float] = 1.0  # For scoring calculations


class AuditFormSchema(BaseModel):
    """Dynamic audit form schema"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    fields: List[AuditFormField]
    total_points: float = 100.0
    passing_score: float = 70.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class AuditAssignment(BaseModel):
    """Audit assignment to auditor"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_reference_id: str
    auditor_id: str
    assigned_by: Optional[str] = None  # admin who assigned, if manual
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: Optional[datetime] = None
    status: AuditStatus = AuditStatus.PENDING
    priority: int = 0  # Higher number = higher priority


class AuditResponse(BaseModel):
    """Auditor's response to audit form"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assignment_id: str
    form_schema_id: str
    responses: Dict[str, Any]  # field_id -> value
    highlights: List[TranscriptHighlight] = []
    overall_score: float = 0.0
    auditor_comments: Optional[str] = None
    flags: List[str] = []  # e.g., ["script_violation", "excellent_service"]
    status: AuditStatus = AuditStatus.DRAFT
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    review_status: Optional[str] = None  # "approved", "rejected", "needs_revision"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class RetentionPolicy(BaseModel):
    """Data retention policy configuration"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    retention_days: int  # 7, 30, 90, etc.
    delete_transcripts: bool = True
    delete_recordings: bool = True
    delete_audit_data: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    # Auditor stats
    pending_audits: int = 0
    completed_today: int = 0
    completed_total: int = 0
    daily_quota: int = 0
    completion_percentage: float = 0.0
    average_score: float = 0.0
    
    # Manager stats
    team_total_audits: int = 0
    team_avg_score: float = 0.0
    team_compliance_rate: float = 0.0
    flagged_audits: int = 0
    pending_review: int = 0


class TrendData(BaseModel):
    """Trend data point"""
    date: str
    value: float
    label: str


class ReportSummary(BaseModel):
    """Comprehensive report summary"""
    period_start: datetime
    period_end: datetime
    total_audits: int
    avg_score: float
    compliance_rate: float
    top_performers: List[Dict[str, Any]]
    low_performers: List[Dict[str, Any]]
    parameter_trends: Dict[str, List[TrendData]]
    flagged_issues: Dict[str, int]
