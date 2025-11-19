#!/usr/bin/env python3
"""
Create Cloud Monitoring dashboard for CUIDA+Care Command Center
"""
import json
import subprocess
import sys
import os

def create_dashboard(dashboard_file: str, project_id: str = "adc-agent"):
    """Create dashboard in Cloud Monitoring"""
    
    with open(dashboard_file, 'r') as f:
        dashboard_config = json.load(f)
    
    # Write to temp file for gcloud
    temp_file = "/tmp/dashboard_config.json"
    with open(temp_file, 'w') as f:
        json.dump(dashboard_config, f)
    
    print(f"📊 Creating dashboard: {dashboard_config['displayName']}")
    
    try:
        result = subprocess.run([
            "gcloud", "monitoring", "dashboards", "create",
            "--config-from-file", temp_file,
            "--project", project_id
        ], capture_output=True, text=True, check=True)
        
        print(f"✅ Dashboard created successfully!")
        print(result.stdout)
        
        # Extract dashboard URL
        if "name:" in result.stdout:
            dashboard_name = result.stdout.split("name:")[1].strip().split()[0]
            dashboard_id = dashboard_name.split("/")[-1]
            print(f"\n🔗 Dashboard URL:")
            print(f"https://console.cloud.google.com/monitoring/dashboards/custom/{dashboard_id}?project={project_id}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create dashboard: {e.stderr}")
        return False
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def main():
    """Create all CUIDA+Care dashboards"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dashboards_dir = os.path.join(script_dir, "..", "monitoring", "dashboards")
    
    print("🚀 Creating CUIDA+Care Cloud Monitoring Dashboards\n")
    
    dashboards = [
        "executive_dashboard.json"
    ]
    
    success_count = 0
    for dashboard in dashboards:
        dashboard_path = os.path.join(dashboards_dir, dashboard)
        if os.path.exists(dashboard_path):
            if create_dashboard(dashboard_path):
                success_count += 1
            print()
        else:
            print(f"⚠️  Dashboard file not found: {dashboard_path}\n")
    
    print(f"\n✅ Created {success_count}/{len(dashboards)} dashboards successfully")
    
    if success_count == len(dashboards):
        print("\n📈 Next steps:")
        print("  1. View dashboards in Cloud Console")
        print("  2. Deploy updated services with monitoring integration")
        print("  3. Verify metrics are being collected")
        print("  4. Set up alert policies")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
