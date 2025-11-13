# C2C Marketplace Backend

FastAPI-based backend implementing the Experiment 2 design for a C2C second-hand marketplace.

## Features
- Mandatory password + 2FA login with risk hooks and JWT sessions
- Product, tag, and search APIs with synonym expansion
- Deals where seller confirmation enforces coupon thresholds and emits cashback
- Membership pricing with platform guardrails (min price, subsidy cap)
- Admin endpoints for parameter versioning, tag moderation, and audit logs
- MySQL persistence via SQLAlchemy 2.0 declarative models

## Getting Started
1. **Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

2. **Configure** `.env`:
   ```env
   DB_URL=mysql+pymysql://user:pass@127.0.0.1:3306/c2c?charset=utf8mb4
   APP_ENV=dev
   JWT_SECRET=change_me
   TWOFA_CHANNELS=email,sms,totp
   ```

3. **Database**
   ```bash
   python -m scripts.create_tables
   python -m scripts.upgrade_schema
   python -m scripts.seed_demo
   ```

4. **Run**
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   or
   
    ```bash
   uvicorn app.main:create_app --reload --factory
   ```

   OpenAPI docs available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Tooling
- Lint: `pylint app`
- Tests: `pytest`

## VS Code Debugging
Launch Uvicorn in reload mode with the provided `.vscode/launch.json` configuration (see below).
