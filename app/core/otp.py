import random
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_models import OTPVerification

logger = logging.getLogger(__name__)

async def send_otp(db: AsyncSession, phone: str, delivery_method: str = "sms") -> str:
    """
    Simulates sending an OTP via SMS or WhatsApp.
    """
    otp_code = str(random.randint(100000, 999119))
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Store in DB
    otp_entry = OTPVerification(
        phone=phone,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(otp_entry)
    await db.commit()
    
    method_label = delivery_method.upper()
    # Simulate sending
    logger.info(f"--- [MOCK {method_label}] Sending OTP {otp_code} to {phone} ---")
    print(f"\n--- [{method_label} OTP SENT] Code {otp_code} sent to {phone} ---\n")
    
    return otp_code

async def verify_otp_code(db: AsyncSession, phone: str, code: str) -> bool:
    """Verify if the OTP is valid and not expired."""
    from sqlalchemy import select, and_
    
    result = await db.execute(
        select(OTPVerification).where(
            and_(
                OTPVerification.phone == phone,
                OTPVerification.otp_code == code,
                OTPVerification.expires_at > datetime.utcnow()
            )
        ).order_by(OTPVerification.created_at.desc())
    )
    otp_entry = result.scalars().first()
    
    if otp_entry:
        # Delete used OTP
        await db.delete(otp_entry)
        await db.commit()
        return True
        
    return False
