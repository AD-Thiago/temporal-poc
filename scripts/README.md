# create_github_repo_and_secret.py

This small helper creates a GitHub repository (user or org) and uploads the `GCP_SA_KEY` Actions secret
from a local JSON key file.

Prerequisites
- Python 3.8+
- Install dependencies: `pip install -r scripts/requirements.txt`
- A GitHub Personal Access Token (PAT) with `repo` scope.

Basic usage

1. From the repo root, install deps:
```
pip install -r scripts/requirements.txt
```

2. Run the script (you will be prompted for the PAT if not provided via `--token` or `GITHUB_TOKEN`):
```
python scripts/create_github_repo_and_secret.py --repo temporal-poc --secret-path github-actions-sa-key.json
```

To create the repo inside an organization and push the local code automatically:
```
python scripts/create_github_repo_and_secret.py --repo temporal-poc --org my-org --push --repo-dir .
```

Notes
- The script encrypts the secret using the repository public key (as required by the GitHub Actions Secrets API).
- Pushing the repo may still require you to provide credentials depending on local Git credential helpers.
