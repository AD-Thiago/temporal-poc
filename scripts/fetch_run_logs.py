#!/usr/bin/env python3
"""
Download and inspect GitHub Actions job logs for a given run/job.

Usage:
  python scripts/fetch_run_logs.py --owner AD-Thiago --repo temporal-poc --job-id 55789224230

You will be prompted for a GitHub PAT.
"""

import argparse
import getpass
import io
import json
import os
import re
import sys
import zipfile

import requests


def download_logs(owner, repo, job_id, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=headers, allow_redirects=True)
    if r.status_code != 200:
        print("Failed to download logs:", r.status_code, r.text)
        sys.exit(1)
    return r.content


def extract_and_search(zip_bytes, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    z.extractall(out_dir)
    print("Extracted files:")
    for name in z.namelist():
        print(" -", name)

    pattern = re.compile(r"ERROR|Error|Traceback|failed|FAILURE", re.I)
    for name in z.namelist():
        try:
            text = z.read(name).decode(errors='ignore')
        except Exception:
            continue
        if pattern.search(text):
            print(f"\n---- Match in: {name}\n")
            lines = text.splitlines()
            for ln in lines[:200]:
                print(ln)
            print("\n---- end snippet\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--job-id", required=True, type=int)
    p.add_argument("--out-dir", default="./run_logs")
    args = p.parse_args()

    token = getpass.getpass("Enter GitHub PAT (token with repo scope): ")
    print("Downloading logs...")
    data = download_logs(args.owner, args.repo, args.job_id, token)
    extract_and_search(data, args.out_dir)


if __name__ == '__main__':
    main()
