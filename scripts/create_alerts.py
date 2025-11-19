"""
Create Cloud Monitoring Alert Policies for CUIDA+Care Command Center
Based on document requirements: 19 mentions of alerting/notifications
"""
import subprocess
import json

ALERTS = [
    {
        "name": "P1-Critical-Error-Rate-High",
        "display_name": "[P1] Error Rate > 5% (Critical)",
        "severity": "CRITICAL",
        "metric": "custom.googleapis.com/cuida_care/error_rate",
        "threshold": 5.0,
        "comparison": "COMPARISON_GT",
        "duration": "60s",
        "notification_channels": []
    },
    {
        "name": "P1-Critical-Job-Latency-High",
        "display_name": "[P1] Job Processing Latency > 5s (Critical)",
        "severity": "CRITICAL",
        "metric": "custom.googleapis.com/cuida_care/job_processing_latency",
        "threshold": 5000.0,  # milliseconds
        "comparison": "COMPARISON_GT",
        "duration": "120s",
        "notification_channels": []
    },
    {
        "name": "P1-Critical-DLQ-Size-Excessive",
        "display_name": "[P1] Dead Letter Queue Size > 50 (Critical)",
        "severity": "CRITICAL",
        "metric": "custom.googleapis.com/cuida_care/dlq_size",
        "threshold": 50.0,
        "comparison": "COMPARISON_GT",
        "duration": "300s",
        "notification_channels": []
    },
    {
        "name": "P2-Warning-Cache-Hit-Rate-Low",
        "display_name": "[P2] Cache Hit Rate < 70% (Warning)",
        "severity": "WARNING",
        "metric": "custom.googleapis.com/cuida_care/cache_hit_rate",
        "threshold": 70.0,
        "comparison": "COMPARISON_LT",
        "duration": "600s",
        "notification_channels": []
    },
    {
        "name": "P2-Warning-Resource-Utilization-High",
        "display_name": "[P2] Resource Utilization > 80% (Warning)",
        "severity": "WARNING",
        "metric": "custom.googleapis.com/cuida_care/resource_utilization",
        "threshold": 80.0,
        "comparison": "COMPARISON_GT",
        "duration": "300s",
        "notification_channels": []
    },
    {
        "name": "P2-Warning-Active-Jobs-High",
        "display_name": "[P2] Active Jobs > 100 (Warning)",
        "severity": "WARNING",
        "metric": "custom.googleapis.com/cuida_care/active_jobs",
        "threshold": 100.0,
        "comparison": "COMPARISON_GT",
        "duration": "180s",
        "notification_channels": []
    },
    {
        "name": "P2-Warning-API-Request-Rate-Low",
        "display_name": "[P2] API Request Rate < 0.1 req/s (Warning)",
        "severity": "WARNING",
        "metric": "custom.googleapis.com/cuida_care/api_request_rate",
        "threshold": 0.1,
        "comparison": "COMPARISON_LT",
        "duration": "900s",  # 15 minutes of low traffic
        "notification_channels": []
    }
]

def create_notification_channel_email(email: str, project_id: str = "adc-agent"):
    """Create email notification channel"""
    config = {
        "type": "email",
        "displayName": f"Email: {email}",
        "labels": {
            "email_address": email
        }
    }
    
    cmd = [
        "gcloud", "alpha", "monitoring", "channels", "create",
        "--channel-content", json.dumps(config),
        "--project", project_id
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Extract channel ID from output
        for line in result.stdout.split('\n'):
            if 'projects/' in line:
                return line.strip()
        return None
    except subprocess.CalledProcessError as e:
        print(f"Failed to create email channel: {e.stderr}")
        return None


def create_alert_policy(alert: dict, project_id: str = "adc-agent"):
    """Create alert policy in Cloud Monitoring"""
    
    policy_config = {
        "displayName": alert["display_name"],
        "documentation": {
            "content": f"Alert triggered when {alert['metric']} crosses threshold {alert['threshold']} for {alert['duration']}",
            "mimeType": "text/markdown"
        },
        "conditions": [
            {
                "displayName": alert["display_name"],
                "conditionThreshold": {
                    "filter": f'metric.type="{alert["metric"]}" AND resource.type="cloud_run_revision"',
                    "comparison": alert["comparison"],
                    "thresholdValue": alert["threshold"],
                    "duration": alert["duration"],
                    "aggregations": [
                        {
                            "alignmentPeriod": "60s",
                            "perSeriesAligner": "ALIGN_MEAN"
                        }
                    ]
                }
            }
        ],
        "combiner": "OR",
        "enabled": True,
        "alertStrategy": {
            "autoClose": "1800s"  # Auto-close after 30 minutes
        },
        "severity": alert["severity"]
    }
    
    # Add notification channels if provided
    if alert["notification_channels"]:
        policy_config["notificationChannels"] = alert["notification_channels"]
    
    # Write to temp file
    import tempfile
    import os
    temp_file = os.path.join(tempfile.gettempdir(), f"alert_{alert['name']}.json")
    with open(temp_file, 'w') as f:
        json.dump(policy_config, f, indent=2)
    
    print(f"\n📢 Creating alert policy: {alert['display_name']}")
    
    cmd = [
        "gcloud", "alpha", "monitoring", "policies", "create",
        "--policy-from-file", temp_file,
        "--project", project_id
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Alert policy created successfully")
        print(f"   Metric: {alert['metric']}")
        print(f"   Threshold: {alert['threshold']}")
        print(f"   Duration: {alert['duration']}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create alert policy: {e.stderr}")
        return False
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    """Create all alert policies"""
    print("🚀 Creating CUIDA+Care Alert Policies\n")
    print("=" * 60)
    
    # Optional: Create notification channel
    email = input("Enter email for notifications (or press Enter to skip): ").strip()
    notification_channels = []
    
    if email:
        print(f"\n📧 Creating email notification channel for {email}")
        channel_id = create_notification_channel_email(email)
        if channel_id:
            print(f"✅ Notification channel created: {channel_id}")
            notification_channels = [channel_id]
        else:
            print("⚠️  Failed to create notification channel, continuing without notifications")
    
    # Create alert policies
    print("\n" + "=" * 60)
    print("Creating Alert Policies...")
    print("=" * 60)
    
    success_count = 0
    for alert in ALERTS:
        alert["notification_channels"] = notification_channels
        if create_alert_policy(alert):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Created {success_count}/{len(ALERTS)} alert policies successfully")
    print("=" * 60)
    
    print("\n📊 Alert Summary:")
    print("  P1 (Critical) Alerts: 3")
    print("    - Error Rate > 5%")
    print("    - Job Latency > 5s")
    print("    - DLQ Size > 50")
    print("  P2 (Warning) Alerts: 4")
    print("    - Cache Hit Rate < 70%")
    print("    - Resource Utilization > 80%")
    print("    - Active Jobs > 100")
    print("    - API Request Rate < 0.1 req/s")
    
    print("\n🔔 Notification Channels:")
    if notification_channels:
        print(f"  ✅ Email: {email}")
    else:
        print("  ⚠️  No notification channels configured")
    
    print("\n📈 Next steps:")
    print("  1. View alert policies in Cloud Console")
    print("  2. Test alerts by triggering thresholds")
    print("  3. Add Slack/SMS notification channels")
    print("  4. Configure alert escalation policies")
    
    return 0 if success_count == len(ALERTS) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
