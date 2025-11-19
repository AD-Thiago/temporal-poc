"""
Cloud Monitoring integration for CUIDA+Care Command Center
Exports custom metrics to Google Cloud Monitoring
"""
from typing import Dict, Any, Optional
from datetime import datetime
from google.cloud import monitoring_v3
from google.api import metric_pb2 as ga_metric
from google.api import label_pb2 as ga_label

from ..src.config import config
from ..src.logging_config import get_logger

logger = get_logger(__name__)


class CloudMonitoringExporter:
    """Export custom metrics to Cloud Monitoring"""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or config.project_id
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{self.project_id}"
        
        # Metric type prefix
        self.metric_prefix = "custom.googleapis.com/cuida_care"
        
        logger.info("Cloud Monitoring exporter initialized", project_id=self.project_id)
    
    def create_metric_descriptor(
        self,
        metric_type: str,
        display_name: str,
        description: str,
        metric_kind: str = "GAUGE",
        value_type: str = "DOUBLE",
        labels: Optional[Dict[str, str]] = None
    ):
        """Create a custom metric descriptor"""
        full_metric_type = f"{self.metric_prefix}/{metric_type}"
        
        descriptor = ga_metric.MetricDescriptor()
        descriptor.type = full_metric_type
        descriptor.metric_kind = getattr(ga_metric.MetricDescriptor.MetricKind, metric_kind)
        descriptor.value_type = getattr(ga_metric.MetricDescriptor.ValueType, value_type)
        descriptor.display_name = display_name
        descriptor.description = description
        
        # Add labels if provided
        if labels:
            for label_key, label_desc in labels.items():
                label = ga_label.LabelDescriptor()
                label.key = label_key
                label.value_type = ga_label.LabelDescriptor.ValueType.STRING
                label.description = label_desc
                descriptor.labels.append(label)
        
        try:
            descriptor = self.client.create_metric_descriptor(
                name=self.project_name,
                metric_descriptor=descriptor
            )
            logger.info(
                "Created metric descriptor",
                metric_type=full_metric_type,
                display_name=display_name
            )
            return descriptor
        except Exception as e:
            if "already exists" in str(e):
                logger.debug("Metric descriptor already exists", metric_type=full_metric_type)
            else:
                logger.error(
                    "Failed to create metric descriptor",
                    metric_type=full_metric_type,
                    error=str(e)
                )
            return None
    
    def write_time_series(
        self,
        metric_type: str,
        value: float,
        resource_type: str = "cloud_run_revision",
        resource_labels: Optional[Dict[str, str]] = None,
        metric_labels: Optional[Dict[str, str]] = None
    ):
        """Write a time series data point"""
        full_metric_type = f"{self.metric_prefix}/{metric_type}"
        
        series = monitoring_v3.TimeSeries()
        series.metric.type = full_metric_type
        
        # Add metric labels
        if metric_labels:
            for key, val in metric_labels.items():
                series.metric.labels[key] = val
        
        # Set resource
        series.resource.type = resource_type
        if resource_labels:
            for key, val in resource_labels.items():
                series.resource.labels[key] = val
        else:
            # Default Cloud Run resource labels
            series.resource.labels["project_id"] = self.project_id
            series.resource.labels["service_name"] = "cuida-care-api"
            series.resource.labels["revision_name"] = "latest"
            series.resource.labels["location"] = "us-central1"
        
        # Add data point
        now = datetime.utcnow()
        seconds = int(now.timestamp())
        nanos = int((now.timestamp() - seconds) * 10**9)
        
        interval = monitoring_v3.TimeInterval(
            {"end_time": {"seconds": seconds, "nanos": nanos}}
        )
        point = monitoring_v3.Point({
            "interval": interval,
            "value": {"double_value": value}
        })
        series.points = [point]
        
        try:
            self.client.create_time_series(
                name=self.project_name,
                time_series=[series]
            )
            logger.debug(
                "Wrote time series",
                metric_type=full_metric_type,
                value=value
            )
        except Exception as e:
            logger.error(
                "Failed to write time series",
                metric_type=full_metric_type,
                error=str(e)
            )
    
    def initialize_cuida_care_metrics(self):
        """Initialize all CUIDA+Care custom metrics"""
        
        # Golden Signals metrics
        metrics = [
            # Latency (ms)
            {
                "metric_type": "job_processing_latency",
                "display_name": "Job Processing Latency",
                "description": "Time taken to process a job (milliseconds)",
                "metric_kind": "GAUGE",
                "value_type": "DOUBLE",
                "labels": {"status": "Job completion status (completed/failed)"}
            },
            # Traffic (requests/sec)
            {
                "metric_type": "api_request_rate",
                "display_name": "API Request Rate",
                "description": "Number of API requests per second",
                "metric_kind": "GAUGE",
                "value_type": "DOUBLE",
                "labels": {"endpoint": "API endpoint path"}
            },
            # Errors (%)
            {
                "metric_type": "error_rate",
                "display_name": "Error Rate",
                "description": "Percentage of failed requests",
                "metric_kind": "GAUGE",
                "value_type": "DOUBLE",
                "labels": {"service": "Service name"}
            },
            # Saturation (%)
            {
                "metric_type": "resource_utilization",
                "display_name": "Resource Utilization",
                "description": "Resource usage percentage (CPU, memory, connections)",
                "metric_kind": "GAUGE",
                "value_type": "DOUBLE",
                "labels": {
                    "resource_type": "Type of resource (cpu/memory/connections)",
                    "service": "Service name"
                }
            },
            # Cache Performance
            {
                "metric_type": "cache_hit_rate",
                "display_name": "Cache Hit Rate",
                "description": "Percentage of cache hits vs total requests",
                "metric_kind": "GAUGE",
                "value_type": "DOUBLE",
                "labels": {"cache_type": "Type of cache (redis/local)"}
            },
            # Job Queue Depth
            {
                "metric_type": "job_queue_depth",
                "display_name": "Job Queue Depth",
                "description": "Number of jobs waiting in queue",
                "metric_kind": "GAUGE",
                "value_type": "INT64"
            },
            # Active Jobs
            {
                "metric_type": "active_jobs",
                "display_name": "Active Jobs",
                "description": "Number of jobs currently being processed",
                "metric_kind": "GAUGE",
                "value_type": "INT64"
            },
            # Dead Letter Queue Size
            {
                "metric_type": "dlq_size",
                "display_name": "Dead Letter Queue Size",
                "description": "Number of messages in dead letter queue",
                "metric_kind": "GAUGE",
                "value_type": "INT64"
            }
        ]
        
        for metric in metrics:
            self.create_metric_descriptor(**metric)
        
        logger.info("Initialized all CUIDA+Care custom metrics")


# Global exporter instance
_exporter: Optional[CloudMonitoringExporter] = None


def get_monitoring_exporter() -> CloudMonitoringExporter:
    """Get or create Cloud Monitoring exporter"""
    global _exporter
    if _exporter is None:
        _exporter = CloudMonitoringExporter()
    return _exporter


def export_golden_signals(
    latency_ms: float,
    request_rate: float,
    error_rate: float,
    cpu_utilization: float,
    memory_utilization: float
):
    """Export Golden Signals metrics to Cloud Monitoring"""
    exporter = get_monitoring_exporter()
    
    exporter.write_time_series("job_processing_latency", latency_ms, metric_labels={"status": "completed"})
    exporter.write_time_series("api_request_rate", request_rate, metric_labels={"endpoint": "/api/v1/jobs"})
    exporter.write_time_series("error_rate", error_rate, metric_labels={"service": "cuida-care-api"})
    exporter.write_time_series("resource_utilization", cpu_utilization, metric_labels={"resource_type": "cpu", "service": "cuida-care-api"})
    exporter.write_time_series("resource_utilization", memory_utilization, metric_labels={"resource_type": "memory", "service": "cuida-care-api"})
    
    logger.info(
        "Exported Golden Signals",
        latency_ms=latency_ms,
        request_rate=request_rate,
        error_rate=error_rate,
        cpu_util=cpu_utilization,
        mem_util=memory_utilization
    )
