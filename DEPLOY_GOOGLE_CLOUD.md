# Deploy auf Google Cloud Run - Kostenlos mit Google Workspace

**Du hast Google Workspace → Kostenloser GCP Account!**

---

## ✅ **Warum Google Cloud Run?**

| Feature | Railway | Google Cloud Run |
|---------|---------|-----------------|
| Kostenlos Tier | 30 Tage | ∞ (unbegrenzt) |
| Monatliches Kontingent | Nein | 2 Millionen Requests |
| Speicher | Bezahlt | 0,40 USD/GB |
| Python/Docker | ✅ | ✅ |
| Skalierung | Auto | Auto |
| Preis danach | $5-50/Mo | ~$0.30-1/Monat |

**GCP ist günstiger und hat echtes kostenloses Tier!**

---

## 🚀 **Google Cloud Run Setup (15 Minuten)**

### **Step 1: Google Cloud Console öffnen**

```
https://console.cloud.google.com
```

Login mit deinem **Google Workspace Account**

---

### **Step 2: Neues Projekt erstellen**

1. Klicke oben rechts das **Project Dropdown**
2. Klicke **"NEW PROJECT"**
3. Name: `handwerk-ml`
4. Klicke **"CREATE"**
5. Warte ~1 Minute bis Projekt erstellt ist

---

### **Step 3: Cloud Run aktivieren**

1. Gehe zu: **APIs & Services** → **Library**
2. Suche: `Cloud Run API`
3. Klicke **"ENABLE"**

---

### **Step 4: Docker Image zu Google Artifact Registry pushen**

Öffne PowerShell und führe aus:

```powershell
# 1. Installiere Google Cloud CLI
# https://cloud.google.com/sdk/docs/install-windows

# 2. Authenticate
gcloud auth login

# 3. Setze Projekt
gcloud config set project handwerk-ml

# 4. Konfiguriere Docker für GCP
gcloud auth configure-docker us-central1-docker.pkg.dev

# 5. Gehe zum Backend Folder
cd C:\Dev\HandwerkML\backend

# 6. Build Docker Image
docker build -t us-central1-docker.pkg.dev/handwerk-ml/handwerk-ml/fastapi:latest .

# 7. Push zu Google Artifact Registry
docker push us-central1-docker.pkg.dev/handwerk-ml/handwerk-ml/fastapi:latest
```

---

### **Step 5: Deploy zu Cloud Run**

```powershell
gcloud run deploy handwerk-ml-api \
  --image us-central1-docker.pkg.dev/handwerk-ml/handwerk-ml/fastapi:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --timeout 3600
```

**Das wars!** 🎉

GCP gibt dir eine URL:
```
https://handwerk-ml-api-xxxxx-uc.a.run.app
```

---

## 🎯 **Alternativ: Einfacher mit gcloud deploy**

Wenn du **gcloud CLI** installiert hast, ist es noch einfacher:

```powershell
# 1. Authenticate
gcloud auth login

# 2. Setze Projekt
gcloud config set project handwerk-ml

# 3. Deploy direkt (ohne Docker lokal zu bauen)
gcloud run deploy handwerk-ml-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

GCP baut automatisch das Docker Image und deployed es!

---

## 📊 **Nach dem Deploy**

Deine App läuft unter:
```
https://handwerk-ml-api-xxxxx-uc.a.run.app/docs
```

✅ Alle 28 Endpoints funktionieren
✅ Swagger UI verfügbar
✅ Automatische Skalierung
✅ HTTPS included

---

## 💰 **Kosten**

**Kostenlos pro Monat:**
- 2.000.000 Requests
- 360.000 GB-Sekunden CPU
- 180.000 GB-Sekunden Memory

**Danach:**
- Zusätzliche Requests: $0.40 pro 1 Mio
- CPU: $0.0000417 pro GB-Sekunde
- Memory: $0.0000083 pro GB-Sekunde

**Realistische Kosten für dich:**
- 1.000 Benutzer täglich = **$0** (im kostenlosen Tier)
- 100.000 Benutzer täglich = **~$2-5/Monat**

---

## ⚙️ **Umgebungsvariablen konfigurieren**

Nach dem Deploy, füge Umgebungsvariablen hinzu:

1. Öffne Cloud Run Service
2. Klicke **"EDIT & DEPLOY NEW REVISION"**
3. Gehe zu **"Runtime settings"**
4. Füge unter **"Environment variables"** ein:

```
ENVIRONMENT=production
SECRET_KEY=<generiere: python -c "import secrets; print(secrets.token_urlsafe(32))">
REQUIRE_HTTPS=true
DATABASE_URL=postgresql://...  (optional - für PostgreSQL)
```

5. Klicke **"DEPLOY"**

---

## 🗄️ **Optionale PostgreSQL Database**

Wenn du die beste Datenbank-Erfahrung willst:

1. Gehe zu **Cloud SQL** in GCP Console
2. Klicke **"CREATE INSTANCE"**
3. Wähle **"PostgreSQL"**
4. Config:
   - Instance ID: `handwerk-ml-db`
   - Password: Sicheres Passwort
   - Region: `us-central1`
   - Machine type: `db-f1-micro` (kostenlos Tier)
5. Klicke **"CREATE"**

Connection String:
```
postgresql+asyncpg://USER:PASSWORD@IP:5432/handwerk_ml
```

---

## 📱 **Monitoring & Logs**

In GCP Console unter **Cloud Run**:

```
Logs → Filter
```

Du kannst alle API Requests und Fehler sehen!

---

## 🚀 **Kurze Checkliste**

- [ ] Google Cloud Console geöffnet
- [ ] Neues Projekt `handwerk-ml` erstellt
- [ ] Cloud Run API aktiviert
- [ ] gcloud CLI installiert
- [ ] Mit `gcloud auth login` authentifiziert
- [ ] `docker build` erfolgreich
- [ ] `gcloud run deploy` erfolgreich
- [ ] URL öffnen und `/docs` testen

---

## 💡 **Probleme?**

### Docker Image zu groß
```powershell
# Kleiner bauen
docker build --no-cache -t ... .
```

### gcloud CLI nicht gefunden
```powershell
# Installiere:
# https://cloud.google.com/sdk/docs/install-windows
# Oder nutze Cloud Shell in Browser!
```

### Memory zu low
```powershell
# Erhöhe auf 1GB
gcloud run deploy handwerk-ml-api \
  --memory 1Gi \
  ...
```

---

## 🎯 **Noch einfacher: Cloud Shell**

Du brauchst nicht mal gcloud lokal!

1. Öffne: https://console.cloud.google.com
2. Klicke Terminal Icon oben rechts
3. Cloud Shell öffnet sich im Browser
4. Führe Befehle aus:

```bash
# Clone dein GitHub Repo
git clone https://github.com/DuKro90/handwerk-ml.git
cd handwerk-ml/backend

# Deploy
gcloud run deploy handwerk-ml-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**Fertig in 5 Minuten!** ☁️

---

## 📞 **Support**

**Google Cloud Docs**: https://cloud.google.com/run/docs

---

## 🏆 **Empfehlung**

**Für dich**: **Google Cloud Run**
- ✅ Mit Google Workspace kostenlos
- ✅ Besseres kostenloses Tier als Railway
- ✅ Professionelle Infrastruktur
- ✅ Für 1000+ Benutzer immer noch kostenlos

**Starte jetzt!**
