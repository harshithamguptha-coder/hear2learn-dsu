"""Keep the foundation deliberately small: browser-based speech recognition
converts speech to text, and this API stores and broadcasts those text results.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .attendance_api import router as attendance_router
from .auth_api import router as auth_router
from .database import init_db
from .notes_api import router as notes_router
from .services.auth_service import AuthService
from .services.notes_service import NotesService
from .services.realtime import EventHub
from .services.translation_service import TranslationService
from .translation_api import router as translation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare application-wide resources when the server starts."""
    init_db()
    app.state.event_hub = EventHub()
    app.state.auth_service = AuthService()
    app.state.notes_service = NotesService()
    app.state.translation_service = TranslationService()
    yield
    await app.state.translation_service.close()


app = FastAPI(
    title="Accessible Classroom API",
    version="0.1.0",
    lifespan=lifespan,
)

# Vite runs on port 5173 by default. These origins are only needed when the
# browser calls this API directly instead of using Vite's development proxy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(attendance_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(translation_router, prefix="/api")
