from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from models.booking import BookingModel, BookingStatus
from models.activity import ActivityModel
from models.user import UserModel, UserRole
from serializers.booking import BookingCreate, BookingSchema, BookingUpdate, BookingWithDetails, BookingStats
from database import get_db
from dependencies.get_current_user import get_current_user
from sqlalchemy.orm import joinedload

router = APIRouter()

def ensure_aware_datetime(dt):
    """Ensure a datetime is timezone aware (UTC)"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

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
    
    # Check if activity exists 
    activity = db.query(ActivityModel).filter(
        ActivityModel.id == booking.activity_id
    ).first()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {booking.activity_id} not found "
        )
    
    # Check if activity is in the past
    now = datetime.now(timezone.utc)
    activity_date_aware = ensure_aware_datetime(activity.date_time)
    
    if activity_date_aware < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book past activities"
        )
    
    # Validate tickets number
    if booking.tickets_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of tickets must be at least 1"
        )
    
    # Check capacity
    spots_available = activity.max_capacity - activity.current_capacity
    if booking.tickets_number > spots_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough spots available. Only {spots_available} spot{'s' if spots_available != 1 else ''} remaining."
        )
    
    # Check if user already booked this activity
    existing_booking = db.query(BookingModel).filter(
        BookingModel.user_id == current_user.id,
        BookingModel.activity_id == booking.activity_id
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already booked this activity. Check your profile to view or modify your booking."
        )
    
    try:
        # Determine booking status based on activity date 
        if activity_date_aware.date() < now.date():
            initial_status = BookingStatus.PAST
        elif activity_date_aware.date() == now.date():
            initial_status = BookingStatus.TODAY
        else:
            initial_status = BookingStatus.UPCOMING
        
        # Create new booking with pre-calculated status
        new_booking = BookingModel(
            user_id=current_user.id,
            activity_id=booking.activity_id,
            tickets_number=booking.tickets_number,
            status=initial_status  
        )
        
        # Update activity capacity
        activity.current_capacity += booking.tickets_number
        
        # Add both objects to session
        db.add(new_booking)
        db.commit()
        
        # Load the booking with all relationships for the response
        booking_with_details = db.query(BookingModel).options(
            joinedload(BookingModel.activity),
            joinedload(BookingModel.user)
        ).filter(BookingModel.id == new_booking.id).first()
        
        return booking_with_details
        
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
     
    
    # Execute query
    bookings = query.order_by(BookingModel.booked_at.desc()).all()

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
    ).filter(BookingModel.id == booking_id).first()
    
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
    booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    
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
    
    # Get activity
    activity = db.query(ActivityModel).filter(ActivityModel.id == booking.activity_id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated activity not found"
        )
    
    # Check if activity is in the past
    activity_date_aware = ensure_aware_datetime(activity.date_time)
    if activity_date_aware < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update booking for past activities"
        )
    
    # Handle tickets number update
    if booking_update.tickets_number is not None:
        # Minimum 1 ticket
        if booking_update.tickets_number < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of tickets must be at least 1"
            )
        
        # Calculate ticket difference
        ticket_diff = booking_update.tickets_number - booking.tickets_number
        
        if ticket_diff != 0:
            # Check capacity
            spots_available = activity.max_capacity - activity.current_capacity + booking.tickets_number
            if booking_update.tickets_number > spots_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough spots available. Only {spots_available} spot{'s' if spots_available != 1 else ''} available for this booking."
                )
            
            # Update activity capacity
            activity.current_capacity += ticket_diff
    
    # Update booking
    update_data = booking_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(booking, key, value)
    
    # Update status
    booking.update_status()
    
    try:
        db.commit()
        db.refresh(booking)
        return booking
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update booking. Please try again."
        )

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
    booking = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    
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
    
    # Get activity
    activity = db.query(ActivityModel).filter(ActivityModel.id == booking.activity_id).first()
    if activity:
        # Check if activity is in the past
        activity_date_aware = ensure_aware_datetime(activity.date_time)
        if activity_date_aware < datetime.now(timezone.utc):
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

@router.get("/availability/{activity_id}")
async def check_booking_availability(
    activity_id: int,
    tickets_number: int = Query(1, ge=1, description="Number of tickets to check availability for"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Check if a booking is available for an activity.
    This helps frontend validate before attempting to book.
    """
    # Check if activity exists 
    activity = db.query(ActivityModel).filter(
        ActivityModel.id == activity_id
    ).first()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found "
        )
    
    # Check if activity is in the past
    now = datetime.now(timezone.utc)
    activity_date_aware = ensure_aware_datetime(activity.date_time)
    
    if activity_date_aware < now:
        return {
            "available": False,
            "message": "Cannot book past activities"
        }
    
    # Check capacity
    spots_left = activity.max_capacity - activity.current_capacity
    if spots_left <= 0:
        return {
            "available": False,
            "message": "This activity is sold out"
        }
    
    if tickets_number > spots_left:
        return {
            "available": False,
            "message": f"Only {spots_left} spot{'s' if spots_left != 1 else ''} available"
        }
    
    # Check if user already booked this activity
    if current_user.role != UserRole.ADMIN.value:
        existing_booking = db.query(BookingModel).filter(
            BookingModel.user_id == current_user.id,
            BookingModel.activity_id == activity_id
        ).first()
        
        if existing_booking:
            return {
                "available": False,
                "message": "You have already booked this activity"
            }
    
    return {
        "available": True,
        "spots_left": spots_left,
        "message": f"{spots_left} spot{'s' if spots_left != 1 else ''} available",
        "activity": {
            "id": activity.id,
            "title": activity.title,
            "date_time": activity.date_time.isoformat(),
            "price": float(activity.price) if activity.price else 0.0,
            "max_capacity": activity.max_capacity,
            "current_capacity": activity.current_capacity
        }
    }
