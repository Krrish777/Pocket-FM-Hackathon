"""API router aggregator — mounts every versioned sub-router under one `APIRouter`.

Mirrors the tiangolo `api/main.py` pattern: sub-routers declare their own prefix/tags; this module
just collects them. The app factory mounts this aggregate under `settings.api_v1_str`.
"""

from fastapi import APIRouter

from story_engine.api.routers import episodes, play

api_router = APIRouter()
api_router.include_router(episodes.router)
api_router.include_router(play.router)
