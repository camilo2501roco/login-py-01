# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

User registration REST API built with FastAPI + MongoDB Atlas + Gmail SMTP. Spanish-language project (comments, error messages, email content in Spanish).

## Commands

```bash
# Setup
python -m venv venv && venv/Scripts/activate && pip install -r requirements.txt

# Run dev server (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
```

## Architecture

MVT-adapted pattern for API:

- **`models/`** — Pydantic v2 schemas (`BaseModel`, `EmailStr`, `field_validator`). Three schemas per entity: input (validation), response (safe output), and InDB (internal MongoDB document shape). Never expose `hashed_password` or `confirmation_token` in response schemas.
- **`controllers/`** — Async business logic functions. Receive validated Pydantic models, interact with MongoDB via Motor, return response models. Use `BackgroundTasks` for non-blocking operations (email sending).
- **`routes/`** — FastAPI `APIRouter` definitions only. Thin layer that wires HTTP methods to controller functions. All routes mounted under `/api/users` prefix in `main.py`.
- **`database/`** — Motor `AsyncIOMotorClient` singleton. `connect_db()`/`close_db()` managed by FastAPI lifespan. Controllers access collections via `get_database()["collection_name"]`. Unique indexes created on startup.
- **`helpers/`** — Pure utility functions: password hashing (bcrypt, rounds=12), email sending (Gmail SMTP SSL port 465 via `smtplib`).

## Key Conventions

- Database operations are **async** (Motor). Email sending is sync but runs in FastAPI `BackgroundTasks` to avoid blocking responses.
- Environment variables loaded from `.env` via `python-dotenv`. Never commit `.env`.
- MongoDB documents use `email` field with a unique index as the duplicate-prevention safety net (controllers also check before insert).
- Pydantic v2 syntax: use `field_validator` (not deprecated `validator`), `model_config` (not `class Config`).
- Password validation enforces: 8+ chars, at least one uppercase, one lowercase, one digit.
