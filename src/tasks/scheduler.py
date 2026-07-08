"""Task scheduler for automated jobs."""

import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class Scheduler:
    """Task scheduler for automated jobs."""
    
    def __init__(self):
        self.jobs = {}
        self.running = False
    
    def register_job(self, name: str, func, interval_minutes: int):
        """Register a job."""
        self.jobs[name] = {
            "func": func,
            "interval": interval_minutes,
            "last_run": None,
        }
        logger.info(f"Job registered: {name} (every {interval_minutes} minutes)")
    
    async def start(self):
        """Start the scheduler."""
        self.running = True
        logger.info("Scheduler started")
        
        while self.running:
            now = datetime.utcnow()
            
            for name, job in self.jobs.items():
                if job["last_run"] is None or \
                   (now - job["last_run"]).total_seconds() >= job["interval"] * 60:
                    try:
                        logger.info(f"Running job: {name}")
                        await job["func"]()
                        job["last_run"] = now
                        logger.info(f"Job completed: {name}")
                    except Exception as e:
                        logger.error(f"Job failed: {name} - {str(e)}")
            
            await asyncio.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Scheduler stopped")
