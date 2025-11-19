"""
Initialize Cloud Monitoring metrics for CUIDA+Care Command Center
Run this script once to create all custom metric descriptors
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitoring import get_monitoring_exporter

def main():
    """Initialize all CUIDA+Care metrics in Cloud Monitoring"""
    print("🚀 Initializing CUIDA+Care Cloud Monitoring metrics...")
    
    exporter = get_monitoring_exporter()
    exporter.initialize_cuida_care_metrics()
    
    print("✅ All metrics initialized successfully!")
    print("\n📊 Created metrics:")
    print("  - job_processing_latency (GAUGE, DOUBLE)")
    print("  - api_request_rate (GAUGE, DOUBLE)")
    print("  - error_rate (GAUGE, DOUBLE)")
    print("  - resource_utilization (GAUGE, DOUBLE)")
    print("  - cache_hit_rate (GAUGE, DOUBLE)")
    print("  - job_queue_depth (GAUGE, INT64)")
    print("  - active_jobs (GAUGE, INT64)")
    print("  - dlq_size (GAUGE, INT64)")
    print("\n🎯 Metrics available at: custom.googleapis.com/cuida_care/*")
    print("\n📈 Next steps:")
    print("  1. Deploy updated worker and API to Cloud Run")
    print("  2. Create Grafana dashboards using these metrics")
    print("  3. Set up alert policies in Cloud Monitoring")

if __name__ == "__main__":
    main()
