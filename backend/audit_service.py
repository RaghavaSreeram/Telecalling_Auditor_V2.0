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
        # Get form schema for weighted scoring and compliance check
        form_schema_id = response_data.get("form_schema_id", "default")
        form_schema = await self.db.audit_form_schemas.find_one(
            {"id": form_schema_id}, 
            {"_id": 0}
        )
        
        # Calculate weighted score based on form schema
        overall_score = await self._calculate_weighted_score(
            response_data.get("responses", {}), 
            form_schema
        )
        
        # Determine compliance result
        compliance_result = await self._check_compliance(
            response_data.get("responses", {}),
            overall_score,
            form_schema
        )
        
        response_data["overall_score"] = overall_score
        response_data["compliance_result"] = compliance_result
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
    
    async def _calculate_weighted_score(self, responses: Dict[str, Any], form_schema: Optional[Dict]) -> float:
        """Calculate weighted score from form responses using schema weights"""
        if not form_schema or "fields" not in form_schema:
            # Fallback to simple average if no schema
            return self._calculate_simple_score(responses)
        
        total_weighted_score = 0.0
        total_possible_score = 0.0
        
        for field in form_schema["fields"]:
            field_id = field["id"]
            field_type = field["type"]
            weight = field.get("weight", 1.0)
            
            if field_id not in responses:
                continue
            
            value = responses[field_id]
            normalized_value = self._normalize_field_value(value, field_type, field)
            
            # Calculate contribution to score
            max_value = field.get("max_value", 10.0) if field_type in ["number", "rating"] else 1.0
            field_score = (normalized_value / max_value) * weight
            
            total_weighted_score += field_score
            total_possible_score += weight
        
        # Calculate percentage score out of 100
        if total_possible_score > 0:
            percentage_score = (total_weighted_score / total_possible_score) * 100
            return round(percentage_score, 2)
        
        return 0.0
    
    def _normalize_field_value(self, value: Any, field_type: str, field: Dict) -> float:
        """Normalize field value to numeric score"""
        if field_type in ["number", "rating"]:
            return float(value) if isinstance(value, (int, float)) else 0.0
        
        elif field_type == "checkbox":
            # Checkbox: 1 if true, 0 if false
            return 1.0 if value else 0.0
        
        elif field_type == "select":
            # For select, could map options to scores or use index
            # Here we'll assume yes/no or similar binary options
            if isinstance(value, str):
                # Map common values
                positive_values = ["yes", "true", "pass", "compliant", "excellent", "good"]
                return 1.0 if value.lower() in positive_values else 0.0
            return float(value) if isinstance(value, (int, float)) else 0.0
        
        elif field_type == "text":
            # Text fields don't contribute to score
            return 0.0
        
        return 0.0
    
    def _calculate_simple_score(self, responses: Dict[str, Any]) -> float:
        """Fallback simple scoring method"""
        total_score = 0
        count = 0
        
        for value in responses.values():
            if isinstance(value, (int, float)):
                total_score += value
                count += 1
        
        return (total_score / count) if count > 0 else 0.0
    
    async def _check_compliance(self, responses: Dict[str, Any], overall_score: float, 
                                form_schema: Optional[Dict]) -> str:
        """Check if audit passes compliance thresholds"""
        if not form_schema:
            return "PASS"  # Default to pass if no schema
        
        passing_score = form_schema.get("passing_score", 70.0)
        
        # Check 1: Overall score threshold
        if overall_score < passing_score:
            return "FAIL"
        
        # Check 2: Critical fields must pass
        if "fields" in form_schema:
            for field in form_schema["fields"]:
                if not field.get("critical", False):
                    continue
                
                field_id = field["id"]
                if field_id not in responses:
                    return "FAIL"  # Missing critical field response
                
                value = responses[field_id]
                field_type = field["type"]
                
                # Check if critical field passes
                if field_type == "checkbox":
                    if not value:  # Checkbox must be checked
                        return "FAIL"
                
                elif field_type in ["number", "rating"]:
                    min_value = field.get("min_value", 0)
                    if isinstance(value, (int, float)) and value < min_value:
                        return "FAIL"
                
                elif field_type == "select":
                    # For select, check if value is in acceptable options
                    negative_values = ["no", "false", "fail", "non-compliant", "poor"]
                    if isinstance(value, str) and value.lower() in negative_values:
                        return "FAIL"
        
        return "PASS"
    
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
