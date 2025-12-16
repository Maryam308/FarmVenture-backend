from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from models.activity import ActivityModel
from models.user import UserModel, UserRole
from serializers.activity import ActivityCreate, ActivityUpdate, ActivitySchema
from database import get_db
from dependencies.get_current_user import get_current_user
from sqlalchemy.orm import joinedload

router = APIRouter()

@router.post('/activities', response_model=ActivitySchema, status_code=status.HTTP_201_CREATED)
def create_activity(
    activity: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new activity - ADMIN ONLY.
    
    - **title**: Title of the activity (1-200 characters)
    - **description**: Description (max 255 characters)
    - **date_time**: Date and time of the activity
    - **duration_minutes**: Duration in minutes (default 60)
    - **price**: Price per person
    - **max_capacity**: Maximum number of participants
    """
    # CHECK IF USER IS ADMIN
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create activities"
        )
    
    # Create new activity instance
    new_activity = ActivityModel(
        title=activity.title,
        description=activity.description,
        date_time=activity.date_time,
        duration_minutes=activity.duration_minutes,
        price=activity.price,
        max_capacity=activity.max_capacity,
        user_id=current_user.id 
    )

    # Add to database
    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)

    return new_activity


@router.get('/activities', response_model=List[ActivitySchema])
def get_activities(
    db: Session = Depends(get_db),
    upcoming_only: bool = True,  
    search: Optional[str] = None
):
    """
    Get all activities (public view for all users).
    
    - **upcoming_only**: Only show future activities (default: true)
    - **search**: Search in title or description
    """
    query = db.query(ActivityModel).\
        filter(ActivityModel.is_active == True).\
        options(joinedload(ActivityModel.user))
    
    # Only show upcoming activities
    if upcoming_only:
        query = query.filter(ActivityModel.date_time >= datetime.now())
    
    # Search filter
    if search:
        query = query.filter(
            (ActivityModel.title.ilike(f'%{search}%')) |
            (ActivityModel.description.ilike(f'%{search}%'))
        )
    
    activities = query.all()
    return activities


@router.get('/activities/{activity_id}', response_model=ActivitySchema)
def get_single_activity(activity_id: int, db: Session = Depends(get_db)):
    """
    Get a single activity by ID (public view).
    """
    activity = db.query(ActivityModel).\
        filter(ActivityModel.id == activity_id).\
        options(joinedload(ActivityModel.user)).\
        first()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found"
        )
    
    return activity


@router.put('/activities/{activity_id}', response_model=ActivitySchema)
def update_activity(
    activity_id: int,
    activity_update: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update an activity - ADMIN ONLY.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can update activities"
        )
    
    # Find the activity
    db_activity = db.query(ActivityModel).filter(ActivityModel.id == activity_id).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found"
        )
    
    # Update only provided fields
    update_data = activity_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_activity, key, value)
    
    db.commit()
    db.refresh(db_activity)
    return db_activity


@router.delete('/activities/{activity_id}')
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete an activity - ADMIN ONLY.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can delete activities"
        )
    
    db_activity = db.query(ActivityModel).filter(ActivityModel.id == activity_id).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found"
        )
    
    # Instead of deleting, mark as inactive (soft delete)
    db_activity.is_active = False
    db.commit()
    
    return {"message": f"Activity with id {activity_id} has been deactivated successfully"}


@router.patch('/activities/{activity_id}/toggle')
def toggle_activity_status(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Toggle activity status (active/inactive) - ADMIN ONLY.
    Useful for opening/closing bookings.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can toggle activity status"
        )
    
    db_activity = db.query(ActivityModel).filter(ActivityModel.id == activity_id).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found"
        )
    
    # Toggle status
    db_activity.is_active = not db_activity.is_active
    db.commit()
    
    status_word = "activated" if db_activity.is_active else "deactivated"
    return {"message": f"Activity with id {activity_id} has been {status_word}"}