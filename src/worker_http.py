from flask import Flask, request, jsonify
import base64
import os
import uuid
from datetime import datetime
from sqlalchemy import text
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from .config import config
from .logging_config import get_logger
from .database import get_db_session, init_db, close_db_connections
from .models import Job, EventLog, JobStatus
from .cache import (
    get_cached_job, cache_job, invalidate_job,
    get_cache_stats, close_redis_connection
)

# Initialize logger
logger = get_logger(__name__)

app = Flask(__name__)

# Cloud Monitoring integration
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from monitoring import get_monitoring_exporter
    monitoring_enabled = True
    logger.info("Cloud Monitoring integration enabled")
except ImportError as e:
    monitoring_enabled = False
    logger.warning("Cloud Monitoring not available", error=str(e))

# Prometheus metrics
messages_processed = Counter('messages_processed_total', 'Total messages processed', ['status'])
job_duration = Histogram('job_duration_seconds', 'Job processing duration')
cache_hits = Counter('cache_hits_total', 'Cache hits')
cache_misses = Counter('cache_misses_total', 'Cache misses')
active_jobs = Gauge('active_jobs', 'Number of jobs currently processing')

# Initialize database on startup
@app.before_request
def before_first_request():
    """Initialize database before first request"""
    if not hasattr(app, 'db_initialized'):
        try:
            init_db()
            app.db_initialized = True
            logger.info("Application started", port=config.port)
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))


@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        'status': 'healthy',
        'service': config.logging.service_name,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route("/cache/stats", methods=["GET"])
def cache_stats_endpoint():
    """Cache statistics endpoint"""
    try:
        stats = get_cache_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route("/readiness", methods=["GET"])
def readiness():
    """Readiness check - verifies database and cache connectivity"""
    db_status = 'disconnected'
    cache_status = 'disconnected'
    
    try:
        # Check database
        with get_db_session() as session:
            session.execute(text('SELECT 1'))
        db_status = 'connected'
        
        # Check cache
        cache_stats = get_cache_stats()
        if cache_stats.get('connected'):
            cache_status = 'connected'
        
        if db_status == 'connected' and cache_status == 'connected':
            return jsonify({
                'status': 'ready',
                'database': db_status,
                'cache': cache_status,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'degraded',
                'database': db_status,
                'cache': cache_status,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
            
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return jsonify({
            'status': 'not_ready',
            'database': db_status,
            'cache': cache_status,
            'error': str(e)
        }), 503


@app.route("/pubsub/push", methods=["POST"])
def pubsub_push():
    """HTTP endpoint for Pub/Sub push subscription with database tracking"""
    correlation_id = str(uuid.uuid4())
    
    try:
        envelope = request.get_json()
        if not envelope:
            logger.warning("Bad request: no JSON body", correlation_id=correlation_id)
            return ("Bad Request: no JSON body", 400)

        message = envelope.get("message")
        if not message:
            logger.warning("Bad request: no message field", correlation_id=correlation_id)
            return ("Bad Request: no message field", 400)

        message_id = message.get('messageId', 'unknown')
        data = message.get("data")
        payload = base64.b64decode(data).decode("utf-8") if data else ""
        attributes = message.get('attributes', {})
        
        logger.info(
            "Received Pub/Sub message",
            message_id=message_id,
            correlation_id=correlation_id,
            payload_preview=payload[:100] if payload else None
        )
        
        # Create job and event log in database
        job_id = str(uuid.uuid4())
        
        with get_db_session() as session:
            # Create job record
            job = Job(
                job_id=job_id,
                message_id=message_id,
                status=JobStatus.PROCESSING,
                payload={'data': payload, 'attributes': attributes},
                source='pubsub',
                correlation_id=correlation_id,
                started_at=datetime.utcnow()
            )
            session.add(job)
            
            # Create event log
            event = EventLog(
                event_id=str(uuid.uuid4()),
                event_type='message.received',
                job_id=job_id,
                data={'message_id': message_id, 'payload': payload},
                event_metadata={'attributes': attributes},
                correlation_id=correlation_id
            )
            session.add(event)
            session.flush()
            
            # Process message
            active_jobs.inc()
            start_time = datetime.utcnow()
            
            try:
                result = process_message(payload, attributes)
                
                job.status = JobStatus.COMPLETED
                job.result = result
                job.completed_at = datetime.utcnow()
                
                # Track metrics
                duration = (job.completed_at - start_time).total_seconds()
                job_duration.observe(duration)
                messages_processed.labels(status='success').inc()
                
                # Export to Cloud Monitoring
                if monitoring_enabled:
                    try:
                        exporter = get_monitoring_exporter()
                        exporter.write_time_series("job_processing_latency", duration * 1000, metric_labels={"status": "completed"})
                        exporter.write_time_series("active_jobs", active_jobs._value._value)
                    except Exception as mon_error:
                        logger.warning("Failed to export metrics to Cloud Monitoring", error=str(mon_error))
                
                # Cache the completed job
                job_dict = {
                    'job_id': job.job_id,
                    'message_id': job.message_id,
                    'status': job.status.value,
                    'payload': job.payload,
                    'result': job.result,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'correlation_id': job.correlation_id
                }
                cache_job(job_dict)
                
                logger.info(
                    "Message processed successfully",
                    job_id=job_id,
                    message_id=message_id,
                    correlation_id=correlation_id,
                    duration_seconds=duration
                )
            except Exception as process_error:
                job.status = JobStatus.FAILED
                job.error_message = str(process_error)
                job.retry_count += 1
                
                # Track metrics
                messages_processed.labels(status='failed').inc()
                
                # Invalidate cache if exists
                invalidate_job(job_id)
                
                logger.error(
                    "Message processing failed",
                    job_id=job_id,
                    error=str(process_error),
                    correlation_id=correlation_id
                )
                
                # Check if should send to DLQ
                if job.retry_count >= job.max_retries:
                    job.status = JobStatus.DEAD_LETTER
                    messages_processed.labels(status='dead_letter').inc()
                    logger.warning(
                        "Message moved to dead letter",
                        job_id=job_id,
                        retry_count=job.retry_count,
                        correlation_id=correlation_id
                    )
            finally:
                active_jobs.dec()
        
        return jsonify({"status": "processed", "job_id": job_id}), 200
        
    except Exception as e:
        logger.error(
            "Unexpected error",
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=correlation_id
        )
        return ("Internal Server Error", 500)


def process_message(payload: str, attributes: dict) -> dict:
    """Process message - implement business logic here"""
    return {
        'processed': True,
        'payload_length': len(payload),
        'timestamp': datetime.utcnow().isoformat()
    }


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Close database and cache connections on shutdown"""
    close_db_connections()
    close_redis_connection()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=config.debug)
