# Google Cloud Run Buildpacks QuickFix Guide

## Problem
Google Cloud Run buildpacks failing to detect Python entrypoint with error:
```
ERROR: for Python, provide a main.py or app.py file or set an entrypoint with
"GOOGLE_ENTRYPOINT" env var or by creating a "Procfile" file
```

Despite having all required files:
- ✅ `main.py`
- ✅ `Procfile`
- ✅ `runtime.txt`

---

## Root Cause Analysis

**Why buildpacks fail:**
1. Buildpacks use **Cloud Native Buildpacks (CNB)** specification
2. Python buildpack may not recognize custom `Procfile` format or directory structure
3. Presence of extraneous files (`=1.5.0`, `=2.0.0`, `=3.0.0` pip artifacts) confuses detection
4. Buildpacks need Python dependencies to be detectable (requirements.txt, setup.py, etc.)

---

## Solution 1: Force Dockerfile Deployment (RECOMMENDED ✅)

Instead of using buildpacks, force Google Cloud Run to use your **Dockerfile directly**:

### In Cloud Shell:
```bash
cd ~/handwerk-ml/backend

gcloud run deploy handwerk-ml-api \
  --source . \
  --dockerfile ./Dockerfile \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 3600
```

**Key difference**: Added `--dockerfile ./Dockerfile` flag

**Why this works**:
- Bypasses buildpacks entirely
- Uses explicit Dockerfile you've tested
- Dockerfile is proven to work (Python 3.11, uvicorn)
- No autodetection needed

**Expected result**: ✅ Build succeeds (takes 3-5 minutes)

---

## Solution 2: Clean Directory + .gcloudignore (FALLBACK)

If Solution 1 fails, create `.gcloudignore` to exclude problematic files:

### Create `.gcloudignore`:
```bash
# Exclude Django/old files
manage.py
pytest.ini
handwerk_ml/
calculator/
db.sqlite3
documents_storage/

# Exclude pip artifacts
=1.5.0
=2.0.0
=3.0.0

# Exclude Docker Compose (buildpacks don't need it)
docker-compose.yml
Dockerfile.celery
Dockerfile.fastapi

# Exclude git and cache
.git/
__pycache__/
*.pyc
.pytest_cache/

# Exclude old requirements
requirements.txt
requirements-minimal.txt
requirements-simple.txt

# Exclude logs and temp
logs/
documents_storage/
.gitignore
*.md
```

Then try deployment with buildpacks:
```bash
gcloud run deploy handwerk-ml-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Solution 3: Set GOOGLE_ENTRYPOINT Env Var (ADVANCED)

If you must use buildpacks, explicitly set entrypoint:

```bash
gcloud run deploy handwerk-ml-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_ENTRYPOINT="uvicorn main:app --host 0.0.0.0 --port 8000"
```

---

## Troubleshooting Checklist

**Before deployment, verify locally:**

```bash
cd C:\Dev\HandwerkML\backend

# 1. Check main.py exists and is valid Python
python -m py_compile main.py
# Expected: No error

# 2. Check requirements are installable
pip install -r requirements_fastapi.txt
# Expected: Success

# 3. Test application locally
uvicorn main:app --host 0.0.0.0 --port 8000
# Expected: "Uvicorn running on http://0.0.0.0:8000"

# 4. Test health endpoint
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

---

## Verification After Deployment

**Once deployed, test the URL:**

```bash
# Get service URL
gcloud run services list

# Test health endpoint
curl https://<SERVICE-URL>/health

# Test API docs
open https://<SERVICE-URL>/docs
```

---

## Common Issues & Fixes

### Issue 1: "Docker image not found"
```
ERROR: docker: invalid reference format
```
**Fix**: Make sure you're in `/backend` directory and `Dockerfile` exists
```bash
pwd  # Should be: .../handwerk-ml/backend
ls -la Dockerfile  # Should exist
```

### Issue 2: "Buildpacks: No matching buildpacks found"
**Fix**: Use `--dockerfile Dockerfile` flag (Solution 1)

### Issue 3: "Application terminated with error code 1"
**Fix**: Check logs:
```bash
gcloud run services logs read handwerk-ml-api
```

### Issue 4: "Out of memory"
**Fix**: Increase memory:
```bash
--memory 1Gi  # Instead of default 512Mi
```

---

## Decision Tree

```
Deploy to Google Cloud Run
    ↓
Try: gcloud run deploy ... --dockerfile ./Dockerfile
    ├─ ✅ SUCCESS → Done! App is running
    ├─ ❌ FAILED → Check error message
    │   ├─ "Docker image error" → Verify Dockerfile exists
    │   ├─ "Out of memory" → Use --memory 1Gi
    │   └─ Other error → Check gcloud run services logs read handwerk-ml-api
    │
    └─ Fallback: Create .gcloudignore + retry buildpacks
```

---

## Success Indicators

✅ **Deployment succeeded** if:
- `Service [handwerk-ml-api] revision [...]  has been deployed`
- URL looks like: `https://handwerk-ml-api-xxxxx-uc.a.run.app`
- Can access `/docs` and see Swagger UI
- Can access `/health` and get `{"status": "healthy"}`

---

## Environment Variables (After Deployment)

If needed, add environment variables:

```bash
gcloud run services update handwerk-ml-api \
  --update-env-vars ENVIRONMENT=production,SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

---

## References

- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- [Cloud Native Buildpacks](https://buildpacks.io/)
- [Python Buildpack](https://github.com/GoogleCloudPlatform/buildpacks/tree/main/cmd/python)
- [Procfile Format](https://devcenter.heroku.com/articles/procfile)

---

## Next Steps

**IMMEDIATE ACTION**: Run Solution 1 in Cloud Shell:

```bash
cd ~/handwerk-ml/backend
gcloud run deploy handwerk-ml-api \
  --source . \
  --dockerfile ./Dockerfile \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 3600
```

Monitor the build output. If it fails, share the **exact error message** and we'll apply the appropriate fix.
