from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.chat import (
    ChatRoomCreate, ChatRoomResponse,
    MessageCreate, MessageResponse,
)
from app.models.booking import BookingResponse
from app.api import deps
from app.db.database import get_db
from app.db.db_models import (
    User, ChatRoom, Message, ServiceRequest, Booking,
)

router = APIRouter()


# ─── Chat Rooms ──────────────────────────────────────────────────────

@router.post("/rooms/", response_model=ChatRoomResponse)
async def create_chat_room(
    room_in: ChatRoomCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Customer initiates a chat with a professional for a service request."""
    # Verify the request exists
    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == room_in.request_id)
    )
    service_request = result.scalar_one_or_none()
    if not service_request:
        raise HTTPException(status_code=404, detail="Service request not found")

    # Check for existing chat room
    existing = await db.execute(
        select(ChatRoom).where(
            ChatRoom.request_id == room_in.request_id,
            ChatRoom.customer_id == current_user.id,
            ChatRoom.professional_id == room_in.professional_id,
        )
    )
    existing_room = existing.scalar_one_or_none()
    if existing_room:
        # Return existing room with names
        pro_result = await db.execute(select(User).where(User.id == existing_room.professional_id))
        pro = pro_result.scalar_one_or_none()
        return ChatRoomResponse(
            id=existing_room.id,
            request_id=existing_room.request_id,
            customer_id=existing_room.customer_id,
            professional_id=existing_room.professional_id,
            status=existing_room.status,
            created_at=existing_room.created_at,
            professional_name=pro.full_name if pro else None,
            customer_name=current_user.full_name,
        )

    # Create new room
    room = ChatRoom(
        request_id=room_in.request_id,
        customer_id=current_user.id,
        professional_id=room_in.professional_id,
    )
    db.add(room)
    await db.flush()
    await db.refresh(room)

    # Add system message
    system_msg = Message(
        chat_room_id=room.id,
        sender_id=current_user.id,
        content=f"Chat started for: {service_request.title}",
        message_type="system",
    )
    db.add(system_msg)
    await db.flush()

    # Get pro name
    pro_result = await db.execute(select(User).where(User.id == room_in.professional_id))
    pro = pro_result.scalar_one_or_none()

    return ChatRoomResponse(
        id=room.id,
        request_id=room.request_id,
        customer_id=room.customer_id,
        professional_id=room.professional_id,
        status=room.status,
        created_at=room.created_at,
        professional_name=pro.full_name if pro else None,
        customer_name=current_user.full_name,
    )


@router.get("/rooms/", response_model=List[ChatRoomResponse])
async def list_chat_rooms(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List user's chat rooms."""
    result = await db.execute(
        select(ChatRoom).where(
            or_(
                ChatRoom.customer_id == current_user.id,
                ChatRoom.professional_id == current_user.id,
            )
        ).order_by(ChatRoom.created_at.desc())
    )
    rooms = result.scalars().all()

    responses = []
    for room in rooms:
        # Get last message
        msg_result = await db.execute(
            select(Message)
            .where(Message.chat_room_id == room.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = msg_result.scalar_one_or_none()

        # Get names
        pro_result = await db.execute(select(User).where(User.id == room.professional_id))
        pro = pro_result.scalar_one_or_none()
        cust_result = await db.execute(select(User).where(User.id == room.customer_id))
        cust = cust_result.scalar_one_or_none()

        responses.append(ChatRoomResponse(
            id=room.id,
            request_id=room.request_id,
            customer_id=room.customer_id,
            professional_id=room.professional_id,
            status=room.status,
            created_at=room.created_at,
            last_message=last_msg.content if last_msg else None,
            professional_name=pro.full_name if pro else None,
            customer_name=cust.full_name if cust else None,
        ))

    return responses


# ─── Messages ────────────────────────────────────────────────────────

@router.get("/rooms/{room_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    room_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get messages in a chat room."""
    # Verify access
    room_result = await db.execute(select(ChatRoom).where(ChatRoom.id == room_id))
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    if current_user.id not in [room.customer_id, room.professional_id]:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(Message)
        .where(Message.chat_room_id == room_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()


@router.post("/rooms/{room_id}/messages", response_model=MessageResponse)
async def send_message(
    room_id: str,
    message_in: MessageCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Send a message (text or price proposal)."""
    # Verify access
    room_result = await db.execute(select(ChatRoom).where(ChatRoom.id == room_id))
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    if current_user.id not in [room.customer_id, room.professional_id]:
        raise HTTPException(status_code=403, detail="Not authorized")
    if room.status != "active":
        raise HTTPException(status_code=400, detail="Chat room is closed")

    # Validate price proposal
    if message_in.message_type == "price_proposal" and message_in.proposed_price is None:
        raise HTTPException(status_code=400, detail="Price proposal requires a proposed_price")

    message = Message(
        chat_room_id=room_id,
        sender_id=current_user.id,
        content=message_in.content,
        message_type=message_in.message_type.value,
        proposed_price=message_in.proposed_price,
        media_url=message_in.media_url,
        duration=message_in.duration,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    await db.refresh(message)

    # Notify recipient
    recipient_id = (
        room.professional_id 
        if current_user.id == room.customer_id 
        else room.customer_id
    )
    
    from app.services.notification_service import send_notification_to_user
    await send_notification_to_user(
        db, 
        recipient_id, 
        f"Message from {current_user.full_name}", 
        message_in.content if message_in.message_type.value == "text" else f"Sent a {message_in.message_type.value}",
        {"chat_id": room_id, "type": "new_message"}
    )

    return message


@router.post("/rooms/{room_id}/accept-price", response_model=BookingResponse)
async def accept_price(
    room_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Accept the last proposed price → auto-creates a Booking."""
    # Get room
    room_result = await db.execute(select(ChatRoom).where(ChatRoom.id == room_id))
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    if current_user.id not in [room.customer_id, room.professional_id]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Find the last price proposal
    msg_result = await db.execute(
        select(Message)
        .where(
            Message.chat_room_id == room_id,
            Message.message_type == "price_proposal",
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    last_proposal = msg_result.scalar_one_or_none()
    if not last_proposal:
        raise HTTPException(status_code=400, detail="No price proposal found to accept")

    # The acceptor must not be the proposer
    if last_proposal.sender_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot accept your own proposal")

    # Get the service request
    req_result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == room.request_id)
    )
    service_request = req_result.scalar_one_or_none()

    # Create acceptance message
    accept_msg = Message(
        chat_room_id=room_id,
        sender_id=current_user.id,
        content=f"Price accepted: ₹{last_proposal.proposed_price}",
        message_type="price_accept",
        proposed_price=last_proposal.proposed_price,
    )
    db.add(accept_msg)

    # Close the chat room
    room.status = "closed"

    # Update service request status
    if service_request:
        service_request.status = "booked"

    # Create the booking
    booking = Booking(
        request_id=room.request_id,
        customer_id=room.customer_id,
        professional_id=room.professional_id,
        agreed_price=last_proposal.proposed_price,
        status="confirmed",
        scheduled_at=service_request.scheduled_at if service_request else None,
    )
    db.add(booking)
    await db.flush()
    await db.refresh(booking)

    # Notify customer
    from app.services.notification_service import send_notification_to_user
    await send_notification_to_user(
        db, 
        room.customer_id, 
        "Booking Confirmed!", 
        f"Your service request '{service_request.title}' is confirmed at ₹{booking.agreed_price}",
        {"booking_id": booking.id, "type": "booking_confirmed"}
    )

    return booking
