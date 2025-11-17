# HandwerkML FastAPI - Hosting-Optionen

**Deutsch**: Verschiedene Wege, um das System online zu hosten

---

## 🏆 Empfohlene Optionen

### 1. **Azure (Microsoft)** ✅ BEST
**Kostenlos**: Ja (kostenlos Tier)
**Schwierigkeit**: Einfach
**Ideal für**: Python FastAPI

```bash
# Azure CLI installieren
# https://learn.microsoft.com/en-us/cli/azure/install-azure-cli

az login
az containerapp up --name handwerk-ml \
  --resource-group myResourceGroup \
  --image myregistry.azurecr.io/handwerk-ml:latest \
  --port 8001 \
  --environment myEnvironment
```

**Vorteile**:
- ✅ Kostenlose Tier für Entwicklung
- ✅ PostgreSQL inklusive
- ✅ Perfect für Python
- ✅ Container Support
- ✅ Gute Dokumentation

---

### 2. **Railway.app** ✅ EMPFOHLEN
**Kostenlos**: Ja ($5/Monat nach kostenlosen Credits)
**Schwierigkeit**: Sehr einfach
**Ideal für**: Schneller Deploy

1. Gehe zu: https://railway.app
2. Sign in mit GitHub
3. Klicke "New Project"
4. Verbinde dein GitHub Repo
5. Railway erkennt `docker-compose.yml` automatisch
6. Klicke Deploy

**Fertig in 5 Minuten!**

---

### 3. **Render.com** ✅ EINFACH
**Kostenlos**: Ja (mit Limitierungen)
**Schwierigkeit**: Einfach
**Ideal für**: FastAPI Services

```yaml
# render.yaml (in Repo root)
services:
  - type: web
    name: handwerk-ml-api
    env: python
    plan: free
    buildCommand: pip install -r requirements_fastapi.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        value: ${DATABASE_URL}
```

Deploy:
1. Push zu GitHub
2. Verbinde Repo mit Render
3. Deploy startet automatisch

---

### 4. **DigitalOcean** ✅ ROBUST
**Kostenlos**: Nein ($5-6/Monat)
**Schwierigkeit**: Mittel
**Ideal für**: Productive Deployments

```bash
# Droplet erstellen (Ubuntu)
# SSH into droplet
git clone https://github.com/your-repo/handwerk-ml.git
cd handwerk-ml/backend

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Deploy with docker-compose
docker-compose up -d
```

**Kostet**:
- Droplet: $5/Monat
- Managed Database: $15/Monat
- Domain: $3/Monat
- **Total**: ~$23/Monat (sehr günstig)

---

### 5. **GitHub Codespaces** ✅ INSTANT
**Kostenlos**: Ja (60 Stunden/Monat)
**Schwierigkeit**: Sehr einfach
**Ideal für**: Schnelles Testing

```
1. Öffne GitHub Repo
2. Klicke "Code" → "Codespaces"
3. "Create codespace on main"
4. Warte 2 Minuten
5. Terminal öffnet sich
6. Führe aus: python -m uvicorn main:app --port 8001
7. Klicke "Ports" → "Forward port"
8. Öffne URL im Browser
```

**Perfekt für**:
- Development
- Testing
- Kleine Projekte
- Kostenlos!

---

### 6. **Vercel** ❌ NICHT IDEAL
**Kostenlos**: Ja
**Schwierigkeit**: Schwer
**Problem**: Vercel ist für Frontend (Next.js, React)

Vercel ist nicht ideal für:
- Full-Stack Python Backend
- 24/7 laufende APIs
- Datenbank-Operationen

**Alternative**: Verwende Vercel nur für Frontend, Backend auf Azure/Railway

---

### 7. **Heroku** ❌ NICHT VERFÜGBAR
Heroku hat kostenlose Tier abgeschafft (seit November 2022).

**Alternativen**: Railway, Render, Azure

---

## 📊 Vergleichstabelle

| Platform | Kosten | Setup | Python | Docker | Database | Empfehlung |
|----------|--------|-------|--------|--------|----------|------------|
| Azure | Kostenlos | Einfach | ✅ | ✅ | ✅ | 🏆 Beste |
| Railway | $5/Mo | Sehr einfach | ✅ | ✅ | ✅ | ⭐ Top |
| Render | Kostenlos | Einfach | ✅ | ✅ | ✅ | ⭐ Top |
| DigitalOcean | $5+/Mo | Mittel | ✅ | ✅ | ✅ | 👍 Robust |
| GitHub Codespaces | Kostenlos | Sehr einfach | ✅ | ❌ | ❌ | 🧪 Testing |
| Vercel | Kostenlos | Schwer | ⚠️ | ❌ | ❌ | ❌ Nicht ideal |

---

## 🚀 Schnellstart: Railway (Empfohlen)

### Step 1: Repository auf GitHub
```bash
cd C:\Dev\HandwerkML\backend
git init
git add .
git commit -m "Initial commit: HandwerkML FastAPI"
git remote add origin https://github.com/YOUR-USERNAME/handwerk-ml.git
git push -u origin main
```

### Step 2: Railway verbinden
1. Öffne https://railway.app
2. Klicke "Login with GitHub"
3. Autorisiere Railway
4. "New Project" → "Deploy from GitHub repo"
5. Wähle `handwerk-ml` Repo
6. Railway erkennt `docker-compose.yml`
7. Klicke "Deploy"

### Step 3: Konfiguriere Umgebung
In Railway Dashboard:
- Settings → Variables
- Setze:
  ```
  ENVIRONMENT=production
  SECRET_KEY=<generiere sicher random Key>
  DATABASE_URL=postgresql://...
  REQUIRE_HTTPS=true
  ```

### Step 4: Fertig!
Railway gibt dir eine URL:
```
https://handwerk-ml-prod.up.railway.app
```

Öffne: `https://handwerk-ml-prod.up.railway.app/docs`

---

## 🚀 Alternative: Azure Container Apps

### Step 1: Azure CLI installieren
```powershell
# Download und Install:
# https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows

# Verify installation
az --version
```

### Step 2: Login zu Azure
```powershell
az login
# Opens browser to authenticate
```

### Step 3: Erstelle Resource Group
```powershell
az group create --name handwerk-ml-rg --location westeurope
```

### Step 4: Container Registry
```powershell
az acr create --resource-group handwerk-ml-rg `
  --name handwerkmlregistry `
  --sku Basic
```

### Step 5: Build & Push Image
```powershell
cd C:\Dev\HandwerkML\backend

# Build FastAPI image
docker build -f Dockerfile.fastapi -t handwerkmlregistry.azurecr.io/fastapi:latest .

# Login to registry
az acr login --name handwerkmlregistry

# Push image
docker push handwerkmlregistry.azurecr.io/fastapi:latest
```

### Step 6: Deploy Container App
```powershell
az containerapp up `
  --name handwerk-ml-api `
  --resource-group handwerk-ml-rg `
  --image handwerkmlregistry.azurecr.io/fastapi:latest `
  --target-port 8000 `
  --ingress external `
  --query properties.configuration.ingress.fqdn
```

### Step 7: Öffne in Browser
```
https://handwerk-ml-api.region.azurecontainerapps.io/docs
```

---

## 💾 PostgreSQL für Production

Alle Hosting-Plattformen unterstützen PostgreSQL.

### Railway PostgreSQL
```bash
# In Railway Dashboard:
# 1. "+ New" → "Database"
# 2. "PostgreSQL"
# 3. Automatisch erstellt!
# 4. CONNECTION STRING wird gesetzt in $DATABASE_URL
```

### Konfiguriere deine App
In `.env` oder Umgebungsvariablen:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/handwerkml
```

---

## 🔒 Sicherheit für Production

### Secrets sichern
```powershell
# NIEMALS in git committen!
# Verwende Environment Variables:

# Railway:
# Settings → Variables → Secret

# Azure:
# Key Vault → Secrets

# Render:
# Environment → Secret
```

### HTTPS aktivieren
```python
# app/config.py
REQUIRE_HTTPS=true
CORS_ORIGINS=["https://your-domain.com"]
```

### SECRET_KEY generieren
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 📊 Meine Empfehlung

**Für schnellen Start**: **Railway.app**
- 5 Minuten Setup
- GitHub Integration
- Docker Support
- Kostenlos erste Monat
- URL: https://railway.app

**Für kostenloses Hosting**: **Render.com**
- Kostenlos Tier
- Automatische Deploys
- URL: https://render.com

**Für Production**: **DigitalOcean**
- $5/Monat für Droplet
- Volle Kontrolle
- URL: https://digitalocean.com

**Für Enterprise**: **Azure**
- Kostenlos Tier
- Skalierbar
- URL: https://azure.microsoft.com

---

## ❌ NICHT empfohlen

- **Vercel**: Nur für Frontend
- **Heroku**: Kostenlos nicht mehr verfügbar
- **GitHub Pages**: Nur statische Seiten
- **VS Code**: Das ist ein Editor, kein Hosting

---

## 🎯 Nächste Schritte

1. **Wähle Platform**: Railway oder Azure
2. **Erstelle GitHub Repo**: Push deinen Code
3. **Verbinde Plattform**: Autorisiere GitHub
4. **Deploy**: 2-5 Minuten
5. **Teste**: Öffne `/docs` Endpoint
6. **Fertig**: Deine App läuft online! 🎉

---

## Support

**Railway Support**: https://railway.app/support
**Azure Support**: https://learn.microsoft.com/en-us/azure/
**Render Support**: https://render.com/docs

---

**Empfehlung**: Starte mit **Railway.app** - es ist am einfachsten! 🚀
