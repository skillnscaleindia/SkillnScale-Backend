import logging
from typing import List, Dict, Optional

try:
    import firebase_admin
    from firebase_admin import messaging, credentials
    _firebase_available = True
except ImportError:
    _firebase_available = False

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.initialized = False
        if not _firebase_available:
            logger.info("firebase-admin not installed. Push notifications will be mocked.")
            return
        try:
            # Check if already initialized (to avoid errors on reload)
            if not firebase_admin._apps:
                # Assuming google-services.json is in root
                try:
                    cred = credentials.Certificate("google-services.json")
                    firebase_admin.initialize_app(cred)
                    self.initialized = True
                    logger.info("Firebase Admin initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to load google-services.json: {e}. Push notifications will be mocked.")
            else:
                self.initialized = True
        except Exception as e:
            logger.error(f"Firebase initialization error: {e}")

    def send_multicast(self, tokens: List[str], title: str, body: str, data: Optional[Dict[str, str]] = None) -> None:
        if not self.initialized:
            logger.info(f"[MOCK PUSH] To: {len(tokens)} devices | Title: {title} | Body: {body} | Data: {data}")
            return

        if not tokens:
            return

        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                tokens=tokens,
            )
            response = messaging.send_multicast(message)
            logger.info(f"Sent notifications: {response.success_count} success, {response.failure_count} failures")
        except Exception as e:
            logger.error(f"Error sending multicast: {e}")

# Global instance
notification_service = NotificationService()

# Helper to avoid circular imports in endpoints if possible, or just import this
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
# Note: Import DeviceToken inside function to avoid potential circular imports if db_models imports this
# But db_models doesn't import this.
from app.db.db_models import DeviceToken

async def send_notification_to_user(
    db: AsyncSession, 
    user_id: str, 
    title: str, 
    body: str, 
    data: Optional[Dict[str, str]] = None
):
    """Fetch user's device tokens and send notification."""
    try:
        result = await db.execute(select(DeviceToken).where(DeviceToken.user_id == user_id))
        tokens = [t.token for t in result.scalars().all()]
        
        if tokens:
            # data values must be strings
            str_data = {k: str(v) for k, v in (data or {}).items()}
            notification_service.send_multicast(tokens, title, body, str_data)
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")
