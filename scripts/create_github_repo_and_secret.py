#!/usr/bin/env python3
"""
Create a GitHub repository and add the `GCP_SA_KEY` Actions secret from a local JSON key.

Usage examples:
  python scripts/create_github_repo_and_secret.py --repo temporal-poc \
    --secret-path "github-actions-sa-key.json"

  # Create in an org and attempt to push local repo directory
  python scripts/create_github_repo_and_secret.py --repo temporal-poc --org my-org --push --repo-dir .
"""

import argparse
import base64
import getpass
import os
import subprocess
import sys

import requests
from nacl import public


def api_request(method, url, token, **kwargs):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    return requests.request(method, url, headers=headers, **kwargs)


def create_repo(token, name, private, description, org=None):
    if org:
        url = f"https://api.github.com/orgs/{org}/repos"
        payload = {"name": name, "private": private, "description": description}
    else:
        url = "https://api.github.com/user/repos"
        payload = {"name": name, "private": private, "description": description}

    r = api_request("POST", url, token, json=payload)
    if r.status_code not in (200, 201):
        print("Failed to create repo:", r.status_code, r.text)
        sys.exit(1)
    return r.json()


def push_local_repo(clone_url, repo_dir):
    # Attempt to set remote and push. This may prompt for credentials depending on local git config.
    subprocess.run(["git", "remote", "remove", "origin"], cwd=repo_dir, check=False)
    subprocess.run(["git", "remote", "add", "origin", clone_url], cwd=repo_dir, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo_dir, check=False)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_dir, check=True)


def encrypt_secret_value(public_key_str, secret_value):
    key_bytes = base64.b64decode(public_key_str)
    pubkey = public.PublicKey(key_bytes)
    sealed_box = public.SealedBox(pubkey)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def put_secret(token, owner, repo, secret_name, secret_value):
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    r = api_request("GET", url, token)
    if r.status_code != 200:
        print("Failed to fetch repository public key:", r.status_code, r.text)
        sys.exit(1)
    key = r.json()
    encrypted = encrypt_secret_value(key["key"], secret_value)
    put_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
    payload = {"encrypted_value": encrypted, "key_id": key["key_id"]}
    r2 = api_request("PUT", put_url, token, json=payload)
    if r2.status_code not in (201, 204):
        print("Failed to put secret:", r2.status_code, r2.text)
        sys.exit(1)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Repository name to create")
    parser.add_argument("--org", help="Organization to create the repo in (optional)")
    parser.add_argument("--private", action="store_true", help="Create a private repository")
    parser.add_argument("--description", default="")
    parser.add_argument("--secret-path", default="github-actions-sa-key.json", help="Path to local JSON key to upload as secret")
    parser.add_argument("--repo-dir", default=".", help="Local git repo directory to push (default: current dir)")
    parser.add_argument("--push", action="store_true", help="Attempt to push the local repo to the new remote")
    parser.add_argument("--token", help="GitHub PAT (optional). If omitted, will read GITHUB_TOKEN env or prompt")
    args = parser.parse_args()

    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token:
        token = getpass.getpass("Enter GitHub PAT (token with repo scope): ")

    print("Creating repository...")
    repo_json = create_repo(token, args.repo, args.private, args.description, org=args.org)
    owner = repo_json["owner"]["login"]
    clone_url = repo_json["clone_url"]
    print(f"Created repo: {owner}/{args.repo}")
    print("Clone URL:", clone_url)

    if args.push:
        try:
            print("Pushing local repo to origin...")
            push_local_repo(clone_url, args.repo_dir)
        except subprocess.CalledProcessError as e:
            print("Push failed:", e)
            print("You can push manually with:")
            print(f"  git remote add origin {clone_url}")
            print("  git push -u origin main")

    if not os.path.exists(args.secret_path):
        print("Secret file not found:", args.secret_path)
        sys.exit(1)
    with open(args.secret_path, "r", encoding="utf-8") as f:
        secret_content = f.read()

    print("Uploading secret GCP_SA_KEY...")
    put_secret(token, owner, args.repo, "GCP_SA_KEY", secret_content)
    print("Secret uploaded successfully.")


if __name__ == "__main__":
    main()
