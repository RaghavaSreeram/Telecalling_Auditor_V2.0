"""
CRM Integration Service
Handles CRM data sync, mapping, and health monitoring
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import logging
import random
from crm_models import (
    CRMRecord, CRMSyncLog, AgentMapping, CRMHealthStats,
    SyncStatus, TranscriptStatus, SyncAction, SyncTrendData
)

logger = logging.getLogger(__name__)


class CRMService:
    """Service for CRM integration and sync management"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_crm_records(
        self,
        user_id: str,
        user_role: str,
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get paginated CRM records with RBAC filtering"""
        match_filter = {}
        
        # Apply RBAC
        if user_role == "auditor":
            # Auditors see only their team's records
            user = await self.db.users.find_one({"id": user_id})
            if user and user.get("team_id"):
                # Get agent mappings for this team
                mappings = await self.db.agent_mappings.find(
                    {"team_id": user["team_id"], "is_active": True}
                ).to_list(1000)
                agent_ids = [m["crm_agent_id"] for m in mappings]
                match_filter["agent_id"] = {"$in": agent_ids}
        
        # Apply additional filters
        if filters:
            if filters.get("call_id"):
                match_filter["call_id"] = {"$regex": filters["call_id"], "$options": "i"}
            if filters.get("agent_id"):
                match_filter["agent_id"] = {"$regex": filters["agent_id"], "$options": "i"}
            if filters.get("crm_user_id"):
                match_filter["crm_user_id"] = {"$regex": filters["crm_user_id"], "$options": "i"}
            if filters.get("campaign_id"):
                match_filter["campaign_id"] = filters["campaign_id"]
            if filters.get("transcript_status"):
                match_filter["transcript_status"] = filters["transcript_status"]
            if filters.get("sync_status"):
                match_filter["sync_status"] = filters["sync_status"]
            if filters.get("date_from"):
                match_filter["call_datetime"] = {"$gte": filters["date_from"]}
            if filters.get("date_to"):
                if "call_datetime" not in match_filter:
                    match_filter["call_datetime"] = {}
                match_filter["call_datetime"]["$lte"] = filters["date_to"]
        
        # Get total count
        total = await self.db.crm_records.count_documents(match_filter)
        
        # Get paginated records
        skip = (page - 1) * page_size
        records = await self.db.crm_records.find(
            match_filter, {"_id": 0}
        ).sort("call_datetime", -1).skip(skip).limit(page_size).to_list(page_size)
        
        return {
            "records": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    async def get_crm_record_details(self, record_id: str, user_id: str, user_role: str) -> Optional[Dict]:
        """Get detailed CRM record with access control"""
        record = await self.db.crm_records.find_one({"id": record_id}, {"_id": 0})
        if not record:
            return None
        
        # Check RBAC
        if user_role == "auditor":
            user = await self.db.users.find_one({"id": user_id})
            if user and user.get("team_id"):
                mapping = await self.db.agent_mappings.find_one({
                    "crm_agent_id": record["agent_id"],
                    "team_id": user["team_id"]
                })
                if not mapping:
                    return None  # Not authorized
        
        # Get sync logs
        sync_logs = await self.db.crm_sync_logs.find(
            {"crm_record_id": record_id}, {"_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(10)
        
        # Get agent mapping
        mapping = await self.db.agent_mappings.find_one(
            {"crm_agent_id": record["agent_id"]}, {"_id": 0}
        )
        
        # Get linked audit
        audit_info = None
        if record.get("audit_id"):
            audit = await self.db.audit_assignments.find_one(
                {"id": record["audit_id"]}, {"_id": 0}
            )
            if audit:
                audit_info = {
                    "id": audit["id"],
                    "status": audit["status"],
                    "auditor_id": audit["auditor_id"],
                    "assigned_at": audit["assigned_at"]
                }
        
        return {
            "record": record,
            "sync_logs": sync_logs,
            "agent_mapping": mapping,
            "audit_info": audit_info
        }
    
    async def resync_crm_record(self, record_id: str, user_id: str) -> Dict[str, Any]:
        """Trigger resync for a CRM record (Manager only)"""
        record = await self.db.crm_records.find_one({"id": record_id})
        if not record:
            raise ValueError("Record not found")
        
        # Simulate CRM API call
        start_time = datetime.now()
        
        try:
            # Mock resync logic - in production, call actual CRM API
            await self._mock_crm_sync(record)
            
            # Update record
            update_data = {
                "sync_status": SyncStatus.SYNCED.value,
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "sync_error": None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.crm_records.update_one(
                {"id": record_id},
                {"$set": update_data}
            )
            
            # Log success
            duration = (datetime.now() - start_time).total_seconds() * 1000
            await self._log_sync(record_id, SyncAction.RESYNC, "success", None, duration)
            
            return {"status": "success", "message": "Resync completed"}
            
        except Exception as e:
            # Log failure
            duration = (datetime.now() - start_time).total_seconds() * 1000
            await self._log_sync(record_id, SyncAction.RESYNC, "failure", str(e), duration)
            
            # Update record with error
            await self.db.crm_records.update_one(
                {"id": record_id},
                {"$set": {
                    "sync_status": SyncStatus.ERROR.value,
                    "sync_error": str(e),
                    "last_sync_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            return {"status": "error", "message": str(e)}
    
    async def validate_mapping(self, record_id: str) -> Dict[str, Any]:
        """Validate and recompute agent mapping"""
        record = await self.db.crm_records.find_one({"id": record_id})
        if not record:
            raise ValueError("Record not found")
        
        # Find agent mapping
        mapping = await self.db.agent_mappings.find_one({
            "crm_agent_id": record["agent_id"],
            "is_active": True
        })
        
        if mapping:
            # Update record with resolved name
            await self.db.crm_records.update_one(
                {"id": record_id},
                {"$set": {"agent_name": mapping["agent_name"]}}
            )
            
            await self._log_sync(record_id, SyncAction.VALIDATE, "success", "Mapping found")
            
            return {
                "status": "success",
                "mapping": mapping,
                "message": "Mapping validated"
            }
        else:
            await self._log_sync(
                record_id, 
                SyncAction.VALIDATE, 
                "failure", 
                "No mapping found for agent"
            )
            
            return {
                "status": "warning",
                "message": "No mapping found for this agent"
            }
    
    async def get_health_stats(self) -> CRMHealthStats:
        """Get CRM integration health statistics"""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        
        # Total records
        total_records = await self.db.crm_records.count_documents({})
        
        # Records synced today
        synced_today = await self.db.crm_records.count_documents({
            "last_sync_at": {"$gte": today_start.isoformat()}
        })
        
        # Failures today
        failures_today = await self.db.crm_sync_logs.count_documents({
            "status": "failure",
            "timestamp": {"$gte": today_start.isoformat()}
        })
        
        # Pending syncs
        pending_syncs = await self.db.crm_records.count_documents({
            "sync_status": SyncStatus.PENDING.value
        })
        
        # Error count
        error_count = await self.db.crm_records.count_documents({
            "sync_status": SyncStatus.ERROR.value
        })
        
        # Average latency
        pipeline = [
            {"$match": {"duration_ms": {"$exists": True}}},
            {"$group": {"_id": None, "avg_latency": {"$avg": "$duration_ms"}}}
        ]
        latency_result = await self.db.crm_sync_logs.aggregate(pipeline).to_list(1)
        avg_latency = latency_result[0]["avg_latency"] if latency_result else 0.0
        
        # Last sync time
        last_record = await self.db.crm_records.find_one(
            {"last_sync_at": {"$exists": True}},
            sort=[("last_sync_at", -1)]
        )
        last_sync_time = last_record.get("last_sync_at") if last_record else None
        if isinstance(last_sync_time, str):
            last_sync_time = datetime.fromisoformat(last_sync_time)
        
        # Success rate
        total_syncs = synced_today + failures_today
        success_rate = ((synced_today / total_syncs) * 100) if total_syncs > 0 else 100.0
        
        return CRMHealthStats(
            last_sync_time=last_sync_time,
            records_synced_today=synced_today,
            failures_today=failures_today,
            average_latency_ms=round(avg_latency, 2),
            total_records=total_records,
            pending_syncs=pending_syncs,
            error_count=error_count,
            success_rate=round(success_rate, 1)
        )
    
    async def get_sync_trends(self, days: int = 7) -> List[SyncTrendData]:
        """Get sync trends for last N days"""
        trends = []
        
        for i in range(days):
            day = datetime.now(timezone.utc) - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day.replace(hour=23, minute=59, second=59)
            
            # Count successes and failures
            pipeline = [
                {
                    "$match": {
                        "timestamp": {
                            "$gte": day_start.isoformat(),
                            "$lte": day_end.isoformat()
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            results = await self.db.crm_sync_logs.aggregate(pipeline).to_list(10)
            
            success_count = 0
            failure_count = 0
            
            for result in results:
                if result["_id"] == "success":
                    success_count = result["count"]
                elif result["_id"] == "failure":
                    failure_count = result["count"]
            
            trends.append(SyncTrendData(
                date=day.strftime("%Y-%m-%d"),
                success_count=success_count,
                failure_count=failure_count,
                total_records=success_count + failure_count
            ))
        
        return list(reversed(trends))
    
    async def retry_failed_syncs(self) -> Dict[str, Any]:
        """Retry all failed syncs (Manager only)"""
        failed_records = await self.db.crm_records.find({
            "sync_status": SyncStatus.ERROR.value
        }).to_list(100)
        
        success_count = 0
        failure_count = 0
        
        for record in failed_records:
            try:
                result = await self.resync_crm_record(record["id"], "system")
                if result["status"] == "success":
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                logger.error(f"Failed to resync {record['id']}: {str(e)}")
                failure_count += 1
        
        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "total_attempted": len(failed_records)
        }
    
    async def _log_sync(
        self, 
        record_id: str, 
        action: SyncAction, 
        status: str, 
        error: Optional[str] = None,
        duration: Optional[float] = None
    ):
        """Log sync operation"""
        log = CRMSyncLog(
            crm_record_id=record_id,
            action=action,
            status=status,
            error_message=error,
            duration_ms=int(duration) if duration else None
        )
        
        log_dict = log.model_dump()
        log_dict["timestamp"] = log_dict["timestamp"].isoformat()
        
        await self.db.crm_sync_logs.insert_one(log_dict)
    
    async def _mock_crm_sync(self, record: Dict):
        """Mock CRM sync - replace with actual CRM API call"""
        # Simulate API delay
        import asyncio
        await asyncio.sleep(0.5)
        
        # Randomly succeed or fail (90% success rate)
        if random.random() < 0.9:
            # Update transcript status
            if random.random() < 0.8:
                record["transcript_status"] = TranscriptStatus.AVAILABLE.value
            return True
        else:
            raise Exception("CRM API timeout")
    
    async def seed_mock_data(self, count: int = 50) -> Dict[str, Any]:
        """Seed database with mock CRM records"""
        import uuid
        
        # Clear existing data
        await self.db.crm_records.delete_many({})
        await self.db.crm_sync_logs.delete_many({})
        
        # Ensure agent mappings exist
        agent_mappings = await self._ensure_agent_mappings()
        
        # Campaigns and queues
        campaigns = [
            {"id": "camp_001", "name": "Q4 Property Launch"},
            {"id": "camp_002", "name": "Luxury Apartments"},
            {"id": "camp_003", "name": "Commercial Spaces"},
            {"id": "camp_004", "name": "Holiday Homes"},
            {"id": "camp_005", "name": "Rental Properties"}
        ]
        queues = ["Inbound Sales", "Outbound Follow-up", "Lead Qualification", "Property Inquiry"]
        
        records = []
        now = datetime.now(timezone.utc)
        
        for i in range(count):
            # Random date within last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            call_datetime = now - timedelta(days=days_ago, hours=hours_ago, minutes=random.randint(0, 59))
            
            # Select random agent and campaign
            agent_map = random.choice(agent_mappings)
            campaign = random.choice(campaigns)
            queue = random.choice(queues)
            
            # Generate call details
            call_id = f"CRM-{uuid.uuid4().hex[:8].upper()}"
            duration = random.randint(120, 900)  # 2-15 minutes
            
            # Determine statuses (90% success, 10% issues)
            is_successful = random.random() < 0.9
            
            if is_successful:
                transcript_status = TranscriptStatus.AVAILABLE
                sync_status = SyncStatus.SYNCED
                transcript_url = f"https://transcripts.example.com/{call_id}.txt"
                transcript_word_count = random.randint(150, 500)
                transcript_last_updated = call_datetime + timedelta(minutes=5)
                sync_error = None
            else:
                transcript_status = random.choice([TranscriptStatus.MISSING, TranscriptStatus.PROCESSING, TranscriptStatus.ERROR])
                sync_status = random.choice([SyncStatus.ERROR, SyncStatus.STALE])
                transcript_url = None
                transcript_word_count = None
                transcript_last_updated = None
                sync_error = random.choice([
                    "Timeout connecting to CRM",
                    "Recording file not found in S3",
                    "Transcript processing failed",
                    "API rate limit exceeded"
                ])
            
            # 70% of calls have audits
            has_audit = random.random() < 0.7
            audit_id = str(uuid.uuid4()) if has_audit else None
            audit_status = random.choice(["pending", "completed"]) if has_audit else None
            
            # Generate S3 URL
            bucket = "telecalling-recordings"
            region = "us-east-1"
            recording_url = f"https://{bucket}.s3.{region}.amazonaws.com/recordings/{call_id}.mp3"
            recording_ref = f"s3://{bucket}/recordings/{call_id}.mp3"
            
            record = CRMRecord(
                call_id=call_id,
                crm_user_id=f"USER-{random.randint(1000, 9999)}",
                agent_id=agent_map["crm_agent_id"],
                agent_name=agent_map["agent_name"],
                campaign_id=campaign["id"],
                campaign_name=campaign["name"],
                queue_name=queue,
                call_datetime=call_datetime,
                call_duration_seconds=duration,
                recording_url=recording_url,
                recording_ref=recording_ref,
                recording_duration=duration,
                transcript_status=transcript_status,
                transcript_url=transcript_url,
                transcript_word_count=transcript_word_count,
                transcript_last_updated=transcript_last_updated,
                sync_status=sync_status,
                last_sync_at=call_datetime + timedelta(minutes=2),
                sync_error=sync_error,
                audit_id=audit_id,
                audit_status=audit_status,
                metadata={
                    "call_direction": random.choice(["inbound", "outbound"]),
                    "call_outcome": random.choice(["interested", "callback", "not_interested", "no_answer"]),
                    "crm_source": "Salesforce Mock"
                },
                created_at=call_datetime,
                updated_at=call_datetime + timedelta(minutes=2)
            )
            
            record_dict = record.model_dump()
            # Convert datetime to ISO strings
            record_dict["call_datetime"] = record_dict["call_datetime"].isoformat()
            record_dict["created_at"] = record_dict["created_at"].isoformat()
            record_dict["updated_at"] = record_dict["updated_at"].isoformat()
            if record_dict.get("transcript_last_updated"):
                record_dict["transcript_last_updated"] = record_dict["transcript_last_updated"].isoformat()
            if record_dict.get("last_sync_at"):
                record_dict["last_sync_at"] = record_dict["last_sync_at"].isoformat()
            
            records.append(record_dict)
        
        await self.db.crm_records.insert_many(records)
        
        # Generate sync logs for each record
        logs = []
        for record in records:
            # Pull log
            pull_log = CRMSyncLog(
                crm_record_id=record["id"],
                action=SyncAction.PULL,
                status="success" if record["sync_status"] == SyncStatus.SYNCED else "failure",
                result="Successfully pulled from CRM" if record["sync_status"] == SyncStatus.SYNCED else "Failed to pull data",
                error_message=record.get("sync_error"),
                duration_ms=random.randint(100, 500),
                timestamp=datetime.fromisoformat(record["created_at"]) + timedelta(seconds=30)
            )
            
            # Map log
            map_log = CRMSyncLog(
                crm_record_id=record["id"],
                action=SyncAction.MAP,
                status="success",
                result="Agent mapping resolved",
                duration_ms=random.randint(50, 150),
                timestamp=datetime.fromisoformat(record["created_at"]) + timedelta(seconds=31)
            )
            
            # Save log
            save_log = CRMSyncLog(
                crm_record_id=record["id"],
                action=SyncAction.SAVE,
                status="success" if record["sync_status"] == SyncStatus.SYNCED else "failure",
                result="Saved to database" if record["sync_status"] == SyncStatus.SYNCED else "Save failed",
                error_message=record.get("sync_error") if record["sync_status"] != SyncStatus.SYNCED else None,
                duration_ms=random.randint(80, 200),
                timestamp=datetime.fromisoformat(record["created_at"]) + timedelta(seconds=32)
            )
            
            logs.extend([pull_log, map_log, save_log])
        
        # Convert logs to dicts with ISO strings
        log_dicts = []
        for log in logs:
            log_dict = log.model_dump()
            log_dict["timestamp"] = log_dict["timestamp"].isoformat()
            log_dicts.append(log_dict)
        
        await self.db.crm_sync_logs.insert_many(log_dicts)
        
        return {
            "success": True,
            "records_created": len(records),
            "logs_created": len(log_dicts),
            "message": f"Successfully seeded {len(records)} CRM records with {len(log_dicts)} sync logs"
        }
    
    async def _ensure_agent_mappings(self) -> List[Dict[str, Any]]:
        """Ensure agent mappings exist"""
        existing = await self.db.agent_mappings.find({}, {"_id": 0}).to_list(length=None)
        
        if existing:
            return existing
        
        # Fetch real users from the database
        users = await self.db.users.find({"role": {"$in": ["auditor", "manager"]}}, {"_id": 0}).to_list(length=100)
        
        if not users:
            # Create default mappings if no users exist
            default_mappings = [
                {
                    "id": str(uuid.uuid4()),
                    "crm_agent_id": f"SF-AGENT-{i:03d}",
                    "app_user_id": str(uuid.uuid4()),
                    "agent_name": f"Agent {chr(65+i)}",
                    "team_id": f"team_{(i % 3) + 1}",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                for i in range(10)
            ]
            await self.db.agent_mappings.insert_many(default_mappings)
            return default_mappings
        
        # Create mappings from existing users
        import uuid
        mappings = []
        for idx, user in enumerate(users[:10]):  # Limit to 10 agents
            mapping = AgentMapping(
                crm_agent_id=f"SF-AGENT-{idx:03d}",
                app_user_id=user["id"],
                agent_name=user.get("full_name", f"Agent {idx+1}"),
                team_id=user.get("team_id", f"team_{(idx % 3) + 1}"),
                is_active=True
            )
            mapping_dict = mapping.model_dump()
            mapping_dict["created_at"] = mapping_dict["created_at"].isoformat()
            mapping_dict["updated_at"] = mapping_dict["updated_at"].isoformat()
            mappings.append(mapping_dict)
        
        if mappings:
            await self.db.agent_mappings.insert_many(mappings)
        
        return mappings
