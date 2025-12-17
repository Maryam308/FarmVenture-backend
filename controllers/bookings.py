from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from models.booking import BookingModel, BookingStatus
from models.activity import ActivityModel
from models.user import UserModel, UserRole
from serializers.booking import BookingCreate, BookingSchema, BookingUpdate, BookingWithDetails, BookingStats
from database import get_db
from dependencies.get_current_user import get_current_user
from sqlalchemy.orm import joinedload

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("/", response_model=BookingSchema, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new booking for an activity.
    Only customers can book activities.
    """
    # Check if user is a customer (not admin)
    if current_user.role == UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot book activities. Please use a customer account."
        )
    
    # Check if activity exists and is active
    activity = db.query(ActivityModel).filter(
        ActivityModel.id == booking.activity_id,
        ActivityModel.is_active == True
    ).first()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {booking.activity_id} not found or inactive"
        )
    
    # Check if activity is in the past
    if activity.date_time < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book past activities"
        )
    
    # Check capacity
    if activity.current_capacity + booking.tickets_number > activity.max_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough spots available. Only {activity.max_capacity - activity.current_capacity} spots left."
        )
    
    # Check if user already booked this activity
    existing_booking = db.query(BookingModel).filter(
        BookingModel.user_id == current_user.id,
        BookingModel.activity_id == booking.activity_id
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already booked this activity"
        )
    
    try:
        # Create new booking
        new_booking = BookingModel(
            user_id=current_user.id,
            activity_id=booking.activity_id,
            tickets_number=booking.tickets_number
        )
        
        # Update booking status based on activity date
        new_booking.update_status()
        
        # Update activity capacity
        activity.current_capacity += booking.tickets_number
        
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        
        return new_booking
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create booking: {str(e)}"
        )

@router.get("/my", response_model=List[BookingWithDetails])
async def get_my_bookings(
    status_filter: Optional[str] = Query(None, description="Filter by status: past, today, upcoming"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get current user's bookings.
    """
    query = db.query(BookingModel).options(
        joinedload(BookingModel.activity),
        joinedload(BookingModel.user)
    ).filter(BookingModel.user_id == current_user.id)
    
    if status_filter:
        if status_filter not in ["past", "today", "upcoming"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status filter must be: past, today, or upcoming"
            )
        query = query.filter(BookingModel.status == status_filter)
    
    # Order by booking date (newest first)
    query = query.order_by(BookingModel.booked_at.desc())
    
    bookings = query.all()
    
    # Update status for each booking
    for booking in bookings:
        booking.update_status()
    db.commit()
    
    return bookings

@router.get("/admin/all", response_model=List[BookingWithDetails])
async def get_all_bookings_admin(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    activity_id: Optional[int] = Query(None, description="Filter by activity ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status: past, today, upcoming"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get all bookings - ADMIN ONLY.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can view all bookings"
        )
    
    query = db.query(BookingModel).options(
        joinedload(BookingModel.activity),
        joinedload(BookingModel.user)
    )
    
    # Apply filters
    if user_id:
        query = query.filter(BookingModel.user_id == user_id)
    
    if activity_id:
        query = query.filter(BookingModel.activity_id == activity_id)
    
    if status_filter:
        if status_filter not in ["past", "today", "upcoming"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status filter must be: past, today, or upcoming"
            )
        query = query.filter(BookingModel.status == status_filter)
    
    # Order by booking date (newest first)
    query = query.order_by(BookingModel.booked_at.desc())
    
    bookings = query.all()
    
    # Update status for each booking
    for booking in bookings:
        booking.update_status()
    db.commit()
    
    return bookings

@router.get("/{booking_id}", response_model=BookingWithDetails)
async def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get a specific booking by ID.
    Users can only see their own bookings, admins can see all.
    """
    booking = db.query(BookingModel).options(
        joinedload(BookingModel.activity),
        joinedload(BookingModel.user)
    ).filter(BookingModel.booking_id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id {booking_id} not found"
        )
    
    # Check permissions
    if current_user.role != UserRole.ADMIN.value and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own bookings"
        )
    
    # Update status
    booking.update_status()
    db.commit()
    
    return booking

@router.put("/{booking_id}", response_model=BookingSchema)
async def update_booking(
    booking_id: int,
    booking_update: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update a booking (e.g., change number of tickets).
    Users can only update their own bookings.
    """
    booking = db.query(BookingModel).filter(BookingModel.booking_id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id {booking_id} not found"
        )
    
    # Check permissions
    if current_user.role != UserRole.ADMIN.value and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own bookings"
        )
    
    # Check if activity is in the past
    activity = db.query(ActivityModel).filter(ActivityModel.id == booking.activity_id).first()
    if activity and activity.date_time < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update booking for past activities"
        )
    
    # Handle tickets number update
    if booking_update.tickets_number is not None:
        if booking_update.tickets_number < 1 or booking_update.tickets_number > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of tickets must be between 1 and 10"
            )
        
        # Calculate ticket difference
        ticket_diff = booking_update.tickets_number - booking.tickets_number
        
        if ticket_diff != 0:
            # Check capacity
            if activity.current_capacity + ticket_diff > activity.max_capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough spots available. Only {activity.max_capacity - activity.current_capacity} spots left."
                )
            
            # Update activity capacity
            activity.current_capacity += ticket_diff
    
    # Update booking
    update_data = booking_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(booking, key, value)
    
    # Update status
    booking.update_status()
    
    db.commit()
    db.refresh(booking)
    
    return booking

@router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Cancel a booking.
    Users can only cancel their own bookings.
    """
    booking = db.query(BookingModel).filter(BookingModel.booking_id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id {booking_id} not found"
        )
    
    # Check permissions
    if current_user.role != UserRole.ADMIN.value and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own bookings"
        )
    
    # Check if activity is in the past
    activity = db.query(ActivityModel).filter(ActivityModel.id == booking.activity_id).first()
    if activity and activity.date_time < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel booking for past activities"
        )
    
    try:
        # Update activity capacity
        if activity:
            activity.current_capacity -= booking.tickets_number
            if activity.current_capacity < 0:
                activity.current_capacity = 0
        
        # Delete booking
        db.delete(booking)
        db.commit()
        
        return {"message": f"Booking {booking_id} has been cancelled successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel booking: {str(e)}"
        )

@router.get("/stats/admin", response_model=BookingStats)
async def get_booking_stats_admin(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get booking statistics - ADMIN ONLY.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can view booking statistics"
        )
    
    try:
        # Update all booking statuses first
        bookings = db.query(BookingModel).all()
        for booking in bookings:
            booking.update_status()
        db.commit()
        
        # Get statistics
        total_bookings = db.query(BookingModel).count()
        upcoming_bookings = db.query(BookingModel).filter(BookingModel.status == BookingStatus.UPCOMING).count()
        today_bookings = db.query(BookingModel).filter(BookingModel.status == BookingStatus.TODAY).count()
        past_bookings = db.query(BookingModel).filter(BookingModel.status == BookingStatus.PAST).count()
        
        # Calculate total tickets
        from sqlalchemy import func
        total_tickets_result = db.query(func.sum(BookingModel.tickets_number)).scalar()
        total_tickets = total_tickets_result if total_tickets_result else 0
        
        return BookingStats(
            total_bookings=total_bookings,
            upcoming_bookings=upcoming_bookings,
            today_bookings=today_bookings,
            past_bookings=past_bookings,
            total_tickets=total_tickets
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get booking statistics: {str(e)}"
        )