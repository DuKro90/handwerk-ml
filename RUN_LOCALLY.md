# Run FastAPI Locally (Windows Native)

Since you have Docker running, use this **simple 3-step approach** on your Windows PowerShell:

---

## Step 1: Start Redis in PowerShell (Terminal 1)

```powershell
docker run -p 6379:6379 redis:7-alpine
```

**Keep this running.** You'll see: `Ready to accept connections`

---

## Step 2: Start FastAPI in PowerShell (Terminal 2)

```powershell
cd C:\Dev\HandwerkML\backend
pip install -r requirements_fastapi.txt
python -m uvicorn main:app --reload --port 8001
```

**Wait for**: `Application startup complete`

---

## Step 3: Test It Works

Open browser or new PowerShell terminal:

```powershell
# Test health
curl http://localhost:8001/health

# Open in browser for interactive testing
Start-Process http://localhost:8001/docs
```

---

## What You'll See

✅ Health endpoint returns:
```json
{"status": "healthy", "timestamp": "..."}
```

✅ Interactive API docs open in browser at:
```
http://localhost:8001/docs
```

---

## Troubleshooting

### Error: "Address already in use" port 8001
```powershell
# Use different port
python -m uvicorn main:app --reload --port 8002
```

### Error: "Cannot connect to Redis"
```powershell
# Make sure Redis is running (check Terminal 1)
# If not, start it again:
docker run -p 6379:6379 redis:7-alpine
```

### Error: "ModuleNotFoundError"
```powershell
pip install -r requirements_fastapi.txt
```

### Error: "Port 6379 already in use"
```powershell
# Kill existing Redis
docker ps
docker kill <container_id>

# Then restart
docker run -p 6379:6379 redis:7-alpine
```

---

## Testing Endpoints

### In Browser (Easiest)
```
http://localhost:8001/docs
```

All 28 endpoints available with "Try it out" buttons!

### Via PowerShell

**Create a project:**
```powershell
$body = @{
    name = "Test Kitchen"
    description = "Modern kitchen with oak finishes"
    project_type = "kitchen"
    region = "Bavaria"
    total_area_sqm = 25
    wood_type = "oak"
    complexity = 3
    final_price = 15000
} | ConvertTo-Json

curl -X POST http://localhost:8001/api/v1/projects/ `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

**List projects:**
```powershell
curl http://localhost:8001/api/v1/projects/
```

**Get health:**
```powershell
curl http://localhost:8001/health
```

---

## Terminal Layout

You'll have 3 PowerShell windows:

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│   Terminal 1        │   Terminal 2        │   Terminal 3        │
│   Redis Running     │   FastAPI Running   │   Testing/Browsing  │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ docker run ...      │ uvicorn main:app... │ http://localhost:... │
│                     │                     │ curl requests       │
│ Ready to accept ... │ Uvicorn running ... │ Browser/PowerShell  │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

---

## Next Steps

1. ✅ Start Redis (Terminal 1)
2. ✅ Start FastAPI (Terminal 2)
3. ✅ Test in browser: http://localhost:8001/docs
4. ✅ Try creating a project
5. ✅ Try listing projects
6. ✅ Try other endpoints

---

## Full Docker Compose Later

Once this works, you can optionally use `docker-compose` to start everything:

```powershell
# From your original PowerShell
cd C:\Dev\HandwerkML\backend
docker-compose up -d

# This starts all 7 services at once
# (You already attempted this - Dockerfiles now exist)
```

But for now, the **3-step approach above is fastest to get running!**

---

## Performance

With just Redis + FastAPI running (no Celery/Qdrant):
- ✅ All API endpoints work
- ✅ Fast responses (<100ms)
- ✅ Data stored in SQLite
- ✅ Background tasks don't run (optional)

For full functionality (embeddings, semantic search):
- Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`
- Start Celery: `celery -A app.celery_app worker --loglevel=info`

But this is **optional for initial testing**.

---

## Status

```
Redis:       🟢 Ready
FastAPI:     🟢 Ready
SQLite DB:   🟢 Ready
Qdrant:      🟡 Optional
Celery:      🟡 Optional
```

Go ahead with Step 1! 🚀
