"""
CRM Integration Models
Data structures for CRM-to-App communication tracking
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


class TranscriptStatus(str, Enum):
    """Transcript availability status"""
    AVAILABLE = "available"
    MISSING = "missing"
    PROCESSING = "processing"
    ERROR = "error"


class SyncStatus(str, Enum):
    """CRM sync status"""
    SYNCED = "synced"
    ERROR = "error"
    STALE = "stale"
    PENDING = "pending"


class SyncAction(str, Enum):
    """Sync action types"""
    PULL = "pull"
    MAP = "map"
    SAVE = "save"
    VALIDATE = "validate"
    RESYNC = "resync"


class CRMRecord(BaseModel):
    """CRM call record with mapping and sync info"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str  # External CRM call ID
    crm_user_id: str  # CRM user/customer ID
    agent_id: str  # CRM agent ID
    agent_name: Optional[str] = None  # Resolved from mapping
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    queue_name: Optional[str] = None
    
    call_datetime: datetime
    call_duration_seconds: Optional[int] = None
    
    recording_url: Optional[str] = None
    recording_ref: Optional[str] = None  # S3 key or reference ID
    recording_duration: Optional[int] = None
    
    transcript_status: TranscriptStatus = TranscriptStatus.MISSING
    transcript_url: Optional[str] = None
    transcript_word_count: Optional[int] = None
    transcript_last_updated: Optional[datetime] = None
    
    sync_status: SyncStatus = SyncStatus.PENDING
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    
    audit_id: Optional[str] = None  # Linked audit assignment ID
    audit_status: Optional[str] = None  # pending/completed
    
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CRMSyncLog(BaseModel):
    """Sync operation log entry"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    crm_record_id: str
    action: SyncAction
    status: str  # "success" or "failure"
    result: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMapping(BaseModel):
    """CRM Agent ID to App User mapping"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4())
    crm_agent_id: str
    app_user_id: str
    agent_name: str
    team_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CRMHealthStats(BaseModel):
    """CRM integration health statistics"""
    last_sync_time: Optional[datetime] = None
    records_synced_today: int = 0
    failures_today: int = 0
    average_latency_ms: float = 0.0
    total_records: int = 0
    pending_syncs: int = 0
    error_count: int = 0
    success_rate: float = 100.0


class SyncTrendData(BaseModel):
    """Daily sync trend data"""
    date: str
    success_count: int
    failure_count: int
    total_records: int
