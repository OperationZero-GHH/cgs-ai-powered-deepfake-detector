# CGS DeepFake Shield — Operations Runbook

This runbook covers procedures for deploying, maintaining, rolling back, rotating secrets, and updating models for CGS DeepFake Shield.

---

## 1. System Architecture Overview

CGS DeepFake Shield comprises three core services:
1. **Next.js Web Service:** Frontend UI, authentication forms, upload interface, dynamic report rendering, dark/light themes.
2. **FastAPI Web API:** Auth, session handling, database transactions, credit management, rate limiting, and durable analysis job queue.
3. **Inference Workers:** Sandboxed background workers executing image, video, and audio deepfake detection models in airgapped offline mode.

---

## 2. Deployment Procedures

### 2.1 Local Development (No Docker Required)
1. **Backend Setup:**
   ```bash
   cd apps/api
   uv venv --python 3.12 .venv
   .\.venv\Scripts\activate
   uv pip install -r requirements.txt
   python -m app.download_model
   python -m app.migrate
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Worker Process (Separate Terminal):**
   ```bash
   cd apps/api
   .\.venv\Scripts\activate
   python -m app.worker
   ```
3. **Frontend Setup (Separate Terminal):**
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

### 2.2 Production Container Deployment (Docker Compose)
1. Ensure `.env` is populated with strong production secrets (see Section 4).
2. Build and launch services:
   ```bash
   docker compose up -d --build
   ```
3. Run database migrations:
   ```bash
   docker compose exec api python -m app.migrate
   ```
4. Verify health status:
   ```bash
   curl -f http://127.0.0.1:8000/health/ready
   curl -f http://127.0.0.1:8000/health/live
   ```

---

## 3. Safe Model Updates & Supply-Chain Rollout

To update or replace a detection model, follow this zero-risk supply-chain procedure:

1. **Verify Integrity & License:**
   - Confirm the target model repository provides SafeTensors format (`.safetensors`).
   - Confirm the license allows your use case (permissive or approved commercial license).
   - Ensure the model does NOT require `trust_remote_code=True`.
2. **Obtain Pinned Commit Hash & SHA-256:**
   - Retrieve the exact 40-character Git commit hash.
   - Download the model weights once in an isolated sandbox.
   - Compute the SHA-256 digest:
     ```bash
     sha256sum model.safetensors
     ```
3. **Update `models.lock.json`:**
   - Add or update the model entry with repo ID, revision, file list, and computed SHA-256.
4. **Implement / Update Model Adapter:**
   - Implement the `ImageDetector` or `AudioDetector` protocol in `app/adapters/`.
   - Implement `predict()` with explicit normalization, softmax, and NaN/Inf guards.
   - Add unit tests verifying `p_fake` output bounds `[0.0, 1.0]`.
5. **Update `docs/MODELS.md` & `docs/DECISIONS.md`:**
   - Document the new model, commit hash, limitations, and decision rationale.
6. **Deploy & Validate Startup Check:**
   - Deploy worker. On startup, the worker hashes all weights against `models.lock.json`. If hashes match, worker starts; if any mismatch, it refuses to start.

---

## 4. Secret Rotation Procedures

### 4.1 Rotate `APP_SECRET_KEY`
`APP_SECRET_KEY` signs guest session cookies and hashes rate-limit keys and IPs.
1. Generate a new 64-character URL-safe secret:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. Update `APP_SECRET_KEY` in `.env`.
3. Restart API and worker services:
   ```bash
   docker compose restart api worker
   ```
   *Note: Rotating `APP_SECRET_KEY` invalidates existing guest cookies; users will receive a fresh guest cookie with default credits.*

### 4.2 Rotate Database Credentials
1. Update user passwords in PostgreSQL:
   ```sql
   ALTER USER cgs_app WITH PASSWORD 'new_app_password';
   ALTER USER cgs_migrator WITH PASSWORD 'new_migrator_password';
   ```
2. Update `APP_DB_PASSWORD` and `MIGRATOR_DB_PASSWORD` in `.env`.
3. Restart all application containers:
   ```bash
   docker compose restart api worker
   ```

---

## 5. Rollback Procedures

### 5.1 Application Code Rollback
1. Check out previous Git release/commit:
   ```bash
   git checkout <previous_stable_commit>
   ```
2. If database schema was changed, roll back Alembic migrations:
   ```bash
   python -m alembic downgrade -1
   ```
3. Rebuild and restart containers:
   ```bash
   docker compose up -d --build
   ```

### 5.2 Model Rollback (Kill Switches)
If a model generates anomalous scores, degrades accuracy, or encounters runtime issues:
1. **Kill Switch via Environment Variable:**
   Set the model flag to false in `.env`:
   - `ENABLE_DIMA_MODEL=false`
   - `ENABLE_PRITHIV_MODEL=false`
   - `ENABLE_HARSHASNADE_MODEL=false`
   - `ENABLE_AUDIO_DETECTION=false`
   - `ENABLE_VIDEO_DETECTION=false`
2. Restart workers:
   ```bash
   docker compose restart worker
   ```
3. The ensemble automatically detects disabled models and safely degrades, computing the verdict across remaining healthy models or falling back to `inconclusive`.

---

## 6. Incident Response & Troubleshooting

### 6.1 Worker Queue Saturation
- **Symptom:** Jobs remain in `queued` status for > 30 seconds.
- **Diagnostic:**
  ```bash
  curl http://127.0.0.1:8000/api/v1/admin/overview
  ```
- **Action:** Scale worker instances:
  ```bash
  docker compose up -d --scale worker=3
  ```

### 6.2 Model Hash Mismatch on Startup
- **Symptom:** Worker container exits immediately with error `ModelIntegrityError`.
- **Diagnostic:** Inspect worker logs:
  ```bash
  docker compose logs worker
  ```
- **Resolution:** Re-download corrupted weights or verify `models.lock.json` matches actual weight file hash.

