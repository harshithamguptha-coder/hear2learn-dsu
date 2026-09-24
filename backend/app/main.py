"""Keep the foundation deliberately small: browser-based speech recognition
converts speech to text, and this API stores and broadcasts those text results.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .database import init_db
from .services.realtime import EventHub


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare application-wide resources when the server starts."""
    init_db()
    app.state.event_hub = EventHub()
    yield


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

app.include_router(router, prefix="/api")
