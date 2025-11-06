"""
Audit Queue & Assignment Service
Handles auto-assignment, queue management, and audit workflow
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import logging
from models import (
    AuditAssignment, AuditStatus, AuditResponse, 
    CallReference, TranscriptHighlight
)

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing audit assignments and queue"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_call_reference(self, call_data: Dict[str, Any]) -> str:
        """Create a new call reference from imported data"""
        call_ref = CallReference(**call_data)
        call_dict = call_ref.model_dump()
        call_dict["date_time"] = call_dict["date_time"].isoformat()
        call_dict["imported_at"] = call_dict["imported_at"].isoformat()
        if call_dict.get("retention_until"):
            call_dict["retention_until"] = call_dict["retention_until"].isoformat()
        
        await self.db.call_references.insert_one(call_dict)
        return call_ref.id
    
    async def auto_assign_audits(self, team_id: Optional[str] = None) -> int:
        """
        Auto-assign pending calls to auditors using round-robin
        Returns number of assignments created
        """
        # Get unassigned calls
        unassigned_calls = await self.db.call_references.find({
            "assignment_id": {"$exists": False}
        }).to_list(100)
        
        if not unassigned_calls:
            return 0
        
        # Get available auditors
        auditor_filter = {"role": "auditor", "status": "active"}
        if team_id:
            auditor_filter["team_id"] = team_id
        
        auditors = await self.db.users.find(auditor_filter).to_list(100)
        if not auditors:
            logger.warning("No active auditors found for assignment")
            return 0
        
        # Round-robin assignment
        assignments_created = 0
        for i, call in enumerate(unassigned_calls):
            auditor = auditors[i % len(auditors)]
            
            assignment = AuditAssignment(
                call_reference_id=call["id"],
                auditor_id=auditor["id"],
                due_date=datetime.now(timezone.utc) + timedelta(days=2)
            )
            
            assignment_dict = assignment.model_dump()
            assignment_dict["assigned_at"] = assignment_dict["assigned_at"].isoformat()
            if assignment_dict.get("due_date"):
                assignment_dict["due_date"] = assignment_dict["due_date"].isoformat()
            
            await self.db.audit_assignments.insert_one(assignment_dict)
            
            # Update call reference with assignment
            await self.db.call_references.update_one(
                {"id": call["id"]},
                {"$set": {"assignment_id": assignment.id}}
            )
            
            assignments_created += 1
        
        logger.info(f"Auto-assigned {assignments_created} calls to {len(auditors)} auditors")
        return assignments_created
    
    async def manual_assign(self, call_reference_id: str, auditor_id: str, assigned_by: str) -> str:
        """Manually assign a call to specific auditor"""
        # Check if already assigned
        existing = await self.db.audit_assignments.find_one({
            "call_reference_id": call_reference_id
        })
        
        if existing:
            # Reassign
            await self.db.audit_assignments.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "auditor_id": auditor_id,
                    "assigned_by": assigned_by,
                    "status": AuditStatus.PENDING.value
                }}
            )
            return existing["id"]
        
        assignment = AuditAssignment(
            call_reference_id=call_reference_id,
            auditor_id=auditor_id,
            assigned_by=assigned_by,
            due_date=datetime.now(timezone.utc) + timedelta(days=2)
        )
        
        assignment_dict = assignment.model_dump()
        assignment_dict["assigned_at"] = assignment_dict["assigned_at"].isoformat()
        if assignment_dict.get("due_date"):
            assignment_dict["due_date"] = assignment_dict["due_date"].isoformat()
        
        await self.db.audit_assignments.insert_one(assignment_dict)
        
        await self.db.call_references.update_one(
            {"id": call_reference_id},
            {"$set": {"assignment_id": assignment.id}}
        )
        
        return assignment.id
    
    async def get_auditor_queue(self, auditor_id: str, status: Optional[str] = None) -> List[Dict]:
        """Get audit queue for specific auditor"""
        match_filter = {"auditor_id": auditor_id}
        if status:
            match_filter["status"] = status
        
        pipeline = [
            {"$match": match_filter},
            {
                "$lookup": {
                    "from": "call_references",
                    "localField": "call_reference_id",
                    "foreignField": "id",
                    "as": "call_data"
                }
            },
            {"$unwind": "$call_data"},
            {"$sort": {"assigned_at": -1}}
        ]
        
        assignments = await self.db.audit_assignments.aggregate(pipeline).to_list(1000)
        return assignments
    
    async def save_audit_draft(self, assignment_id: str, responses: Dict[str, Any], 
                               highlights: List[Dict] = None) -> None:
        """Save audit draft for later completion"""
        existing = await self.db.audit_responses.find_one({"assignment_id": assignment_id})
        
        update_data = {
            "responses": responses,
            "status": AuditStatus.DRAFT.value
        }
        
        if highlights:
            update_data["highlights"] = highlights
        
        if existing:
            await self.db.audit_responses.update_one(
                {"id": existing["id"]},
                {"$set": update_data}
            )
        else:
            response = AuditResponse(
                assignment_id=assignment_id,
                form_schema_id="default",  # Should be passed as parameter
                responses=responses,
                highlights=highlights or []
            )
            response_dict = response.model_dump()
            response_dict["started_at"] = response_dict["started_at"].isoformat()
            await self.db.audit_responses.insert_one(response_dict)
    
    async def submit_audit(self, assignment_id: str, response_data: Dict[str, Any]) -> str:
        """Submit completed audit"""
        # Calculate score based on form schema
        overall_score = self._calculate_score(response_data.get("responses", {}))
        
        response_data["overall_score"] = overall_score
        response_data["status"] = AuditStatus.COMPLETED.value
        response_data["submitted_at"] = datetime.now(timezone.utc).isoformat()
        
        existing = await self.db.audit_responses.find_one({"assignment_id": assignment_id})
        
        if existing:
            await self.db.audit_responses.update_one(
                {"id": existing["id"]},
                {"$set": response_data}
            )
            response_id = existing["id"]
        else:
            response = AuditResponse(
                assignment_id=assignment_id,
                **response_data
            )
            response_dict = response.model_dump()
            response_dict["started_at"] = response_dict["started_at"].isoformat()
            response_dict["submitted_at"] = response_dict["submitted_at"]
            await self.db.audit_responses.insert_one(response_dict)
            response_id = response.id
        
        # Update assignment status
        await self.db.audit_assignments.update_one(
            {"id": assignment_id},
            {"$set": {"status": AuditStatus.COMPLETED.value}}
        )
        
        return response_id
    
    def _calculate_score(self, responses: Dict[str, Any]) -> float:
        """Calculate overall score from form responses"""
        # Simplified scoring - should use form schema weights
        total_score = 0
        count = 0
        
        for value in responses.values():
            if isinstance(value, (int, float)):
                total_score += value
                count += 1
        
        return (total_score / count) if count > 0 else 0.0
    
    async def get_dashboard_stats(self, user_id: str, role: str) -> Dict[str, Any]:
        """Get dashboard statistics based on role"""
        if role == "auditor":
            return await self._get_auditor_stats(user_id)
        elif role in ["manager", "admin"]:
            return await self._get_manager_stats(user_id)
        return {}
    
    async def _get_auditor_stats(self, auditor_id: str) -> Dict[str, Any]:
        """Get auditor-specific dashboard stats"""
        # Pending audits
        pending = await self.db.audit_assignments.count_documents({
            "auditor_id": auditor_id,
            "status": AuditStatus.PENDING.value
        })
        
        # Completed today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        completed_today = await self.db.audit_assignments.count_documents({
            "auditor_id": auditor_id,
            "status": AuditStatus.COMPLETED.value,
            "assigned_at": {"$gte": today_start.isoformat()}
        })
        
        # Total completed
        completed_total = await self.db.audit_assignments.count_documents({
            "auditor_id": auditor_id,
            "status": AuditStatus.COMPLETED.value
        })
        
        # Average score
        pipeline = [
            {"$match": {"auditor_id": auditor_id, "status": AuditStatus.COMPLETED.value}},
            {
                "$lookup": {
                    "from": "audit_responses",
                    "localField": "id",
                    "foreignField": "assignment_id",
                    "as": "response"
                }
            },
            {"$unwind": {"path": "$response", "preserveNullAndEmptyArrays": True}},
            {
                "$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$response.overall_score"}
                }
            }
        ]
        
        result = await self.db.audit_assignments.aggregate(pipeline).to_list(1)
        avg_score = result[0]["avg_score"] if result and result[0].get("avg_score") else 0.0
        
        daily_quota = 10  # Should be configurable
        completion_percentage = (completed_today / daily_quota * 100) if daily_quota > 0 else 0
        
        return {
            "pending_audits": pending,
            "completed_today": completed_today,
            "completed_total": completed_total,
            "daily_quota": daily_quota,
            "completion_percentage": round(completion_percentage, 1),
            "average_score": round(avg_score, 2)
        }
    
    async def _get_manager_stats(self, manager_id: str) -> Dict[str, Any]:
        """Get manager-specific dashboard stats"""
        # Get all team members
        team_members = await self.db.users.find({"role": "auditor"}).to_list(100)
        auditor_ids = [m["id"] for m in team_members]
        
        # Total audits
        total_audits = await self.db.audit_assignments.count_documents({
            "auditor_id": {"$in": auditor_ids}
        })
        
        # Average score across team
        pipeline = [
            {"$match": {"auditor_id": {"$in": auditor_ids}}},
            {
                "$lookup": {
                    "from": "audit_responses",
                    "localField": "id",
                    "foreignField": "assignment_id",
                    "as": "response"
                }
            },
            {"$unwind": {"path": "$response", "preserveNullAndEmptyArrays": True}},
            {
                "$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$response.overall_score"},
                    "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}
                }
            }
        ]
        
        result = await self.db.audit_assignments.aggregate(pipeline).to_list(1)
        
        if result and len(result) > 0:
            avg_score = result[0].get("avg_score", 0.0) or 0.0
            completed = result[0].get("completed", 0)
        else:
            avg_score = 0.0
            completed = 0
        
        compliance_rate = (completed / total_audits * 100) if total_audits > 0 else 0
        
        # Flagged audits
        flagged = await self.db.audit_assignments.count_documents({
            "auditor_id": {"$in": auditor_ids},
            "status": AuditStatus.FLAGGED.value
        })
        
        return {
            "team_total_audits": total_audits,
            "team_avg_score": round(avg_score, 2),
            "team_compliance_rate": round(compliance_rate, 1),
            "flagged_audits": flagged,
            "pending_review": 0  # To be implemented
        }
