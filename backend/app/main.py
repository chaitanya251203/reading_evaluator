import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import improvements, materials, reading, students, teachers

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="Reading Assessment API", version="0.1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(students.router, prefix="/students", tags=["students"])
app.include_router(materials.router, prefix="/materials", tags=["materials"])
app.include_router(reading.router, prefix="/reading", tags=["reading"])
app.include_router(teachers.router, prefix="/teachers", tags=["teachers"])
app.include_router(improvements.router, prefix="/improvements", tags=["improvements"])

from fastapi.staticfiles import StaticFiles
import os

frontend_dist = os.path.join(os.path.dirname(__file__), "../../frontend-react/dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

