from flask import Flask, request, jsonify
import base64
import os
import uuid
from datetime import datetime

from .config import config
from .logging_config import get_logger
from .database import get_db_session, init_db, close_db_connections
from .models import Job, EventLog, JobStatus

# Initialize logger
logger = get_logger(__name__)

app = Flask(__name__)

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


@app.route("/readiness", methods=["GET"])
def readiness():
    """Readiness check - verifies database connectivity"""
    try:
        with get_db_session() as session:
            session.execute('SELECT 1')
        
        return jsonify({
            'status': 'ready',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return jsonify({
            'status': 'not_ready',
            'database': 'disconnected',
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
            try:
                result = process_message(payload, attributes)
                
                job.status = JobStatus.COMPLETED
                job.result = result
                job.completed_at = datetime.utcnow()
                
                logger.info(
                    "Message processed successfully",
                    job_id=job_id,
                    message_id=message_id,
                    correlation_id=correlation_id
                )
            except Exception as process_error:
                job.status = JobStatus.FAILED
                job.error_message = str(process_error)
                job.retry_count += 1
                
                logger.error(
                    "Message processing failed",
                    job_id=job_id,
                    error=str(process_error),
                    correlation_id=correlation_id
                )
                
                # Check if should send to DLQ
                if job.retry_count >= job.max_retries:
                    job.status = JobStatus.DEAD_LETTER
                    logger.warning(
                        "Message moved to dead letter",
                        job_id=job_id,
                        retry_count=job.retry_count,
                        correlation_id=correlation_id
                    )
        
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
    """Close database connections on shutdown"""
    close_db_connections()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=config.debug)
