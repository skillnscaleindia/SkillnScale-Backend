from fastapi import APIRouter
from app.api.endpoints import auth, users, services, bookings

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])

@api_router.get("/health")
def health_check():
    return {"status": "ok"}
