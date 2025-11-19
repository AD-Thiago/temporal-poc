"""
Database models for CUIDA+Care Worker
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
import enum

from .database import Base


class JobStatus(str, enum.Enum):
    """Job execution status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class Job(Base):
    """Job execution tracking"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), unique=True, index=True, nullable=False)
    message_id = Column(String(255), index=True)
    
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, index=True)
    
    payload = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    source = Column(String(100), nullable=True)  # pubsub, api, scheduled, etc.
    correlation_id = Column(String(255), index=True, nullable=True)
    
    def __repr__(self):
        return f"<Job(id={self.id}, job_id={self.job_id}, status={self.status})>"


class EventLog(Base):
    """Event audit log"""
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), unique=True, index=True, nullable=False)
    
    event_type = Column(String(100), index=True, nullable=False)  # message.received, job.started, etc.
    job_id = Column(String(255), index=True, nullable=True)
    
    data = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    correlation_id = Column(String(255), index=True, nullable=True)
    
    def __repr__(self):
        return f"<EventLog(id={self.id}, event_type={self.event_type}, timestamp={self.timestamp})>"


class SystemMetric(Base):
    """System metrics for monitoring"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    metric_name = Column(String(100), index=True, nullable=False)
    metric_value = Column(JSON, nullable=False)  # Can store int, float, dict, etc.
    
    labels = Column(JSON, nullable=True)  # Additional labels/dimensions
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<SystemMetric(metric_name={self.metric_name}, timestamp={self.timestamp})>"
