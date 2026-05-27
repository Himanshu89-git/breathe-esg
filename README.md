# Breathe ESG — Emissions Ingestion Platform

A Django REST + React prototype for ingesting, normalising, and reviewing carbon emissions data from SAP, utility portals, and corporate travel platforms.

**Demo credentials:** `analyst / analyst123`

---

## Project Structure

```
breathe-esg/
├── backend/          # Django REST API
├── frontend/         # React + Vite + Tailwind
├── docs/             # MODEL.md, DECISIONS.md, TRADEOFFS.md, SOURCES.md
└── sample_data/      # SAP, utility, and travel CSV files for testing
```

---

## Local Development

### Backend

```bash
cd backend

# Create virtualenv
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit env
cp .env.example .env

# Run migrations and seed demo data
python manage.py migrate
python manage.py seed

# Start server
python manage.py runserver
# API at http://localhost:8000
```

### Frontend

```bash
cd frontend

npm install

# Copy env (leave VITE_API_URL blank for local dev — Vite proxies to :8000)
cp .env.example .env

npm run dev
# UI at http://localhost:5173
```

---

## Deployment on Render

### Backend (Web Service)

1. Create a new **Web Service** on [render.com](https://render.com)
2. Connect your GitHub repo, set **Root Directory** to `backend`
3. Set **Build Command**: `./build.sh`
4. Set **Start Command**: `gunicorn breathe_esg.wsgi --bind 0.0.0.0:$PORT`
5. Add environment variables:
   - `SECRET_KEY` — a long random string
   - `DEBUG` — `False`
   - `ALLOWED_HOSTS` — `your-app.onrender.com`
   - `DATABASE_URL` — from a Render PostgreSQL instance
   - `CORS_ALLOWED_ORIGINS` — your frontend URL

### Frontend (Static Site)

1. Create a **Static Site** on Render
2. Set **Root Directory** to `frontend`
3. **Build Command**: `npm install && npm run build`
4. **Publish Directory**: `dist`
5. Add environment variable:
   - `VITE_API_URL` — your backend URL (e.g. `https://breathe-esg-api.onrender.com`)

### Database

Create a **PostgreSQL** instance on Render and copy the Internal Database URL into the backend's `DATABASE_URL` env var.

---

## Running Tests

```bash
cd backend
python manage.py test
```

---

## Uploading Sample Data

After seeding, the dashboard already has demo records. To test file upload:

1. Log in as `analyst / analyst123`
2. Go to **Upload Data**
3. Select source type (SAP / Utility / Travel)
4. Upload one of the files from `sample_data/`:
   - `sap_fuel_export.csv` — SAP MM flat file with German headers
   - `utility_electricity_export.csv` — Portal CSV with Indian DISCOMs
   - `travel_concur_export.csv` — Concur-style travel export

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/token/` | Login → JWT tokens |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| GET | `/api/accounts/me/` | Current user + tenant |
| POST | `/api/ingestion/upload/` | Upload file (multipart) |
| GET | `/api/emissions/records/` | List emission records (paginated, filterable) |
| GET | `/api/emissions/records/stats/` | Dashboard stats |
| POST | `/api/emissions/records/{id}/review/` | Approve / reject / flag |
| POST | `/api/emissions/records/bulk_approve/` | Bulk approve by IDs |
| GET | `/api/emissions/batches/` | List ingestion batches |

---

## Key Design Decisions

See `docs/DECISIONS.md` for full reasoning. Summary:

- **SAP:** Flat file (semicolon/tab delimited) — most accessible format without IT involvement
- **Utility:** Portal CSV export — works across all Indian DISCOMs; PDFs are too fragile
- **Travel:** Concur/Navan CSV export — API requires OAuth admin setup
- **Scope assignment:** Inferred at parse time from activity category, not manual
- **Unit normalisation:** Done at ingest; both original and normalised values stored
- **Auth:** JWT (8h access, 7d refresh) — stateless, works with SPA

See `docs/MODEL.md`, `docs/TRADEOFFS.md`, `docs/SOURCES.md` for full documentation.
