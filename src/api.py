"""
FastAPI REST API for CUIDA+Care Command Center
Provides endpoints to query jobs, metrics, and system statistics
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from .config import config
from .logging_config import get_logger
from .database import get_db_session, get_engine
from .models import Job, EventLog, SystemMetric, JobStatus
from .cache import (
    get_cached_job, cache_job, get_cache_stats,
    CacheKey, cache_get, cache_set
)

logger = get_logger(__name__)

# Metrics (will be imported from prometheus_client if needed)
try:
    from prometheus_client import Counter
    cache_hits = Counter('api_cache_hits_total', 'Total cache hits')
    cache_misses = Counter('api_cache_misses_total', 'Total cache misses')
except ImportError:
    # Fallback if prometheus_client not available
    class DummyCounter:
        def inc(self): pass
    cache_hits = DummyCounter()
    cache_misses = DummyCounter()

# FastAPI app
app = FastAPI(
    title="CUIDA+Care Command Center API",
    description="REST API for job management, metrics, and system monitoring",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Pydantic Models
class JobResponse(BaseModel):
    """Job response model"""
    job_id: str
    message_id: Optional[str] = None
    status: str
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Paginated job list response"""
    total: int
    page: int
    limit: int
    jobs: List[JobResponse]


class JobStatsResponse(BaseModel):
    """Job statistics response"""
    total_jobs: int
    by_status: Dict[str, int]
    avg_duration_seconds: Optional[float] = None
    success_rate: float
    total_retries: int


class SystemHealthResponse(BaseModel):
    """System health response"""
    status: str
    database: str
    cache: str
    timestamp: datetime


class CacheStatsResponse(BaseModel):
    """Cache statistics response"""
    connected: bool
    hit_rate: float
    keyspace_hits: int
    keyspace_misses: int
    total_commands_processed: int
    connected_clients: int
    used_memory_human: str


# Dependency to get database session
def get_db():
    """Dependency to get database session"""
    with get_db_session() as session:
        yield session


# Health & Status Endpoints
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "cuida-care-api",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/status", response_model=SystemHealthResponse, tags=["Health"])
def system_status():
    """
    Complete system status including database and cache
    """
    db_status = "disconnected"
    cache_status = "disconnected"
    
    try:
        # Check database
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        db_status = "connected"
    except Exception as e:
        logger.error("Database check failed", error=str(e), error_type=type(e).__name__)
    
    try:
        # Check cache
        stats = get_cache_stats()
        if stats.get('connected'):
            cache_status = "connected"
    except Exception as e:
        logger.error("Cache check failed", error=str(e))
    
    overall_status = "healthy" if db_status == "connected" and cache_status == "connected" else "degraded"
    
    return SystemHealthResponse(
        status=overall_status,
        database=db_status,
        cache=cache_status,
        timestamp=datetime.utcnow()
    )


@app.get("/cache/stats", response_model=CacheStatsResponse, tags=["Monitoring"])
def cache_statistics():
    """
    Get Redis cache statistics including hit rate and memory usage
    """
    try:
        stats = get_cache_stats()
        if not stats.get('connected'):
            raise HTTPException(status_code=503, detail="Cache not connected")
        
        return CacheStatsResponse(**stats)
    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Job Endpoints
@app.get("/api/v1/jobs", response_model=JobListResponse, tags=["Jobs"])
def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    List jobs with pagination and optional status filter
    
    - **status**: Filter by job status (pending, processing, completed, failed, dead_letter)
    - **page**: Page number (starts at 1)
    - **limit**: Items per page (max 100)
    """
    # Try to get from cache first
    cache_key = CacheKey.job_list(status, page, limit)
    cached_result = cache_get(cache_key)
    
    if cached_result:
        cache_hits.inc()
        logger.debug("Cache hit for job list", status=status, page=page)
        return cached_result
    
    cache_misses.inc()
    
    # Build query
    query = db.query(Job)
    
    if status:
        try:
            status_enum = JobStatus(status)
            query = query.filter(Job.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Get total count
    total = query.count()
    
    # Paginate
    offset = (page - 1) * limit
    jobs = query.order_by(desc(Job.created_at)).offset(offset).limit(limit).all()
    
    # Convert to response models
    job_responses = [JobResponse.from_orm(job) for job in jobs]
    
    result = JobListResponse(
        total=total,
        page=page,
        limit=limit,
        jobs=job_responses
    )
    
    # Cache the result
    cache_set(cache_key, result.dict(), ttl=config.redis.ttl_job)
    
    return result


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
def get_job(job_id: str, db: Session = Depends(get_db)):
    """
    Get a specific job by ID
    
    - **job_id**: Unique job identifier
    """
    # Try cache first
    cached_job = get_cached_job(job_id)
    
    if cached_job:
        cache_hits.inc()
        logger.debug("Cache hit for job", job_id=job_id)
        return JobResponse(**cached_job)
    
    cache_misses.inc()
    
    # Query database
    job = db.query(Job).filter(Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Cache the job
    job_dict = {
        'job_id': job.job_id,
        'message_id': job.message_id,
        'status': job.status.value,
        'payload': job.payload,
        'result': job.result,
        'error_message': job.error_message,
        'retry_count': job.retry_count,
        'max_retries': job.max_retries,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'updated_at': job.updated_at.isoformat() if job.updated_at else None,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'source': job.source,
        'correlation_id': job.correlation_id
    }
    cache_job(job_dict)
    
    return JobResponse.from_orm(job)


@app.get("/api/v1/jobs/stats/summary", response_model=JobStatsResponse, tags=["Jobs"])
def job_statistics(db: Session = Depends(get_db)):
    """
    Get aggregated job statistics
    
    Returns counts by status, success rate, and average duration
    """
    # Try cache first
    cache_key = CacheKey.aggregation("job_stats", "all")
    cached_stats = cache_get(cache_key)
    
    if cached_stats:
        cache_hits.inc()
        return JobStatsResponse(**cached_stats)
    
    cache_misses.inc()
    
    # Query statistics
    total_jobs = db.query(func.count(Job.id)).scalar()
    
    # Count by status
    status_counts = db.query(
        Job.status,
        func.count(Job.id)
    ).group_by(Job.status).all()
    
    by_status = {status.value: count for status, count in status_counts}
    
    # Calculate success rate
    completed = by_status.get('completed', 0)
    failed = by_status.get('failed', 0)
    total_finished = completed + failed
    success_rate = (completed / total_finished * 100) if total_finished > 0 else 0.0
    
    # Average duration for completed jobs
    avg_duration = db.query(
        func.avg(
            func.extract('epoch', Job.completed_at - Job.started_at)
        )
    ).filter(
        Job.status == JobStatus.COMPLETED,
        Job.completed_at.isnot(None),
        Job.started_at.isnot(None)
    ).scalar()
    
    # Total retries
    total_retries = db.query(func.sum(Job.retry_count)).scalar() or 0
    
    stats = JobStatsResponse(
        total_jobs=total_jobs,
        by_status=by_status,
        avg_duration_seconds=float(avg_duration) if avg_duration else None,
        success_rate=round(success_rate, 2),
        total_retries=total_retries
    )
    
    # Cache for 5 minutes
    cache_set(cache_key, stats.dict(), ttl=config.redis.ttl_metrics)
    
    return stats


@app.get("/api/v1/events/{job_id}", tags=["Events"])
def get_job_events(job_id: str, db: Session = Depends(get_db)):
    """
    Get all events for a specific job
    
    - **job_id**: Job identifier
    """
    events = db.query(EventLog).filter(
        EventLog.job_id == job_id
    ).order_by(EventLog.timestamp).all()
    
    if not events:
        raise HTTPException(status_code=404, detail=f"No events found for job {job_id}")
    
    return [
        {
            'event_id': event.event_id,
            'event_type': event.event_type,
            'timestamp': event.timestamp.isoformat() if event.timestamp else None,
            'data': event.data,
            'metadata': event.event_metadata,
            'correlation_id': event.correlation_id
        }
        for event in events
    ]


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(config.port))
