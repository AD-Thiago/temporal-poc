#!/usr/bin/env python3
"""
Dispatch a GitHub Actions workflow and print detailed logs.

This script uses the GitHub Actions REST API to dispatch a workflow and
then lists recent runs and their statuses. It does not require the `gh` CLI.

Usage:
  python scripts/dispatch_workflow.py --repo AD-Thiago/temporal-poc --workflow cloud-run-deploy.yml --ref main

You will be prompted for a GitHub PAT (token with `repo` scope).
"""

import argparse
import getpass
import json
import sys
import time
from datetime import datetime, timezone

import requests


def post_dispatch(owner, repo, workflow, ref, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    payload = {"ref": ref}
    r = requests.post(url, headers=headers, json=payload)
    return r


def list_runs(owner, repo, token, per_page=10):
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs?per_page={per_page}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=headers)
    return r


def pretty_print_response(resp):
    print(f"HTTP {resp.status_code} {resp.reason}")
    try:
        j = resp.json()
        print(json.dumps(j, indent=2, ensure_ascii=False))
    except Exception:
        print(resp.text)


def find_recent_run(runs_json, workflow, ref):
    # Find a run for the workflow and ref created in the last 5 minutes
    now = datetime.now(timezone.utc)
    for run in runs_json.get("workflow_runs", []):
        created_at = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        age = (now - created_at).total_seconds()
        if run.get("head_branch") == ref or run.get("head_branch") == ref.replace('refs/heads/', ''):
            if age < 300:
                return run
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="owner/repo")
    p.add_argument("--workflow", required=True, help="workflow file name (e.g. cloud-run-deploy.yml)")
    p.add_argument("--ref", default="main", help="git ref to run against")
    p.add_argument("--poll-seconds", type=int, default=6, help="seconds between run status polls")
    p.add_argument("--timeout", type=int, default=300, help="timeout seconds to wait for run completion")
    args = p.parse_args()

    if "/" not in args.repo:
        print("--repo must be in the form owner/repo")
        sys.exit(2)
    owner, repo = args.repo.split("/", 1)

    token = getpass.getpass("Enter GitHub PAT (token with repo scope): ")
    print("Dispatching workflow...")
    resp = post_dispatch(owner, repo, args.workflow, args.ref, token)
    if resp.status_code not in (200, 201, 204):
        print("Dispatch failed:")
        pretty_print_response(resp)
        sys.exit(1)
    else:
        print("Dispatch request accepted (expected 204 No Content).")

    # Poll for the newly created run
    t0 = time.time()
    run = None
    while time.time() - t0 < args.timeout:
        r = list_runs(owner, repo, token, per_page=20)
        if r.status_code != 200:
            print("Failed to list runs:")
            pretty_print_response(r)
            sys.exit(1)
        runs_json = r.json()
        run = find_recent_run(runs_json, args.workflow, args.ref)
        if run:
            print("Found recent run:")
            print(json.dumps(run, indent=2, ensure_ascii=False))
            break
        print("No recent run found yet; polling...")
        time.sleep(args.poll_seconds)

    if not run:
        print("No workflow run detected within timeout. Listing last 5 runs for debugging:")
        pretty_print_response(r)
        sys.exit(2)

    run_id = run["id"]
    # Poll run status until completion or timeout
    run_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
    while time.time() - t0 < args.timeout:
        r2 = requests.get(run_url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"})
        if r2.status_code != 200:
            print("Failed to fetch run status:")
            pretty_print_response(r2)
            sys.exit(1)
        run_obj = r2.json()
        status = run_obj.get("status")
        conclusion = run_obj.get("conclusion")
        print(f"Run {run_id} status={status} conclusion={conclusion} url={run_obj.get('html_url')}")
        if status == "completed":
            print("Run completed. Full run object:")
            print(json.dumps(run_obj, indent=2, ensure_ascii=False))
            break
        time.sleep(args.poll_seconds)

    if run_obj.get("conclusion") not in ("success", None):
        print("Run concluded with non-success conclusion:")
        print(run_obj.get("conclusion"))
        sys.exit(3)

    print("Workflow dispatch and monitoring finished successfully.")


if __name__ == "__main__":
    main()
