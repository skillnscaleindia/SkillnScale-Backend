from fastapi import APIRouter
from app.api.endpoints import auth, users, services, bookings, requests, availability, chat, reviews, customer, professional, uploads, notifications, payments

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(requests.router, prefix="/requests", tags=["requests"])
api_router.include_router(availability.router, prefix="/availability", tags=["availability"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(customer.router, prefix="/customer", tags=["customer"])
api_router.include_router(professional.router, prefix="/pro", tags=["professional"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])


@api_router.get("/health")
def health_check():
    return {"status": "ok"}
