"""
Data Retention Cleanup Job
Scheduled task to delete expired transcripts and call data based on retention policies
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta
import logging
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']


async def run_retention_cleanup():
    """Execute retention cleanup based on active policies"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Get active retention policies
        policies = await db.retention_policies.find({"is_active": True}).to_list(100)
        
        if not policies:
            logger.info("No active retention policies found")
            return
        
        for policy in policies:
            logger.info(f"Applying retention policy: {policy['name']} ({policy['retention_days']} days)")
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy['retention_days'])
            logger.info(f"Cutoff date: {cutoff_date.isoformat()}")
            
            # Delete expired call references
            if policy.get('delete_transcripts', True):
                result = await db.call_references.delete_many({
                    "imported_at": {"$lt": cutoff_date.isoformat()}
                })
                logger.info(f"Deleted {result.deleted_count} expired call references")
            
            # Delete orphaned transcripts
            if policy.get('delete_transcripts', True):
                # In production, this would delete from S3/AWS
                logger.info("Transcript cleanup from external storage would run here")
            
            # Optionally delete audit data
            if policy.get('delete_audit_data', False):
                # Get assignments linked to deleted calls
                deleted_assignments = await db.audit_assignments.delete_many({
                    "assigned_at": {"$lt": cutoff_date.isoformat()}
                })
                logger.info(f"Deleted {deleted_assignments.deleted_count} expired assignments")
                
                # Delete responses for deleted assignments
                deleted_responses = await db.audit_responses.delete_many({
                    "started_at": {"$lt": cutoff_date.isoformat()}
                })
                logger.info(f"Deleted {deleted_responses.deleted_count} expired responses")
        
        logger.info("Retention cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Retention cleanup failed: {str(e)}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(run_retention_cleanup())
