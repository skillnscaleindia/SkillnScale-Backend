from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins - using specific ones for security + credentials support
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Add origins from settings if they exist
if settings.BACKEND_CORS_ORIGINS:
    for o in settings.BACKEND_CORS_ORIGINS:
        s_o = str(o).rstrip('/')
        if s_o not in origins:
            origins.append(s_o)

print(f"DEBUG: Active CORS Origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to SkillnScale Backend", "version": "0.1.0"}
