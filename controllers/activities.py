from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import cloudinary
import cloudinary.uploader
import os

from models.activity import ActivityModel
from models.user import UserModel, UserRole
from serializers.activity import ActivityCreate, ActivityUpdate, ActivitySchema
from database import get_db
from dependencies.get_current_user import get_current_user
from sqlalchemy.orm import joinedload

router = APIRouter()

@router.post("/", response_model=ActivitySchema, status_code=status.HTTP_201_CREATED)
def create_activity(
    activity: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new activity - ADMIN ONLY.
    """
    # CHECK IF USER IS ADMIN
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create activities"
        )
    
    # Create new activity instance with ALL fields
    new_activity = ActivityModel(
        title=activity.title,
        description=activity.description,
        date_time=activity.date_time,
        duration_minutes=activity.duration_minutes,
        price=activity.price,
        max_capacity=activity.max_capacity,
        category=activity.category,
        location=activity.location,
        image_url=activity.image_url,
        user_id=current_user.id,
        current_capacity=0,
        is_active=True
    )

    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)
    return new_activity

@router.get("/", response_model=List[ActivitySchema])
def get_activities(
    db: Session = Depends(get_db),
    upcoming_only: bool = Query(True, description="Only show upcoming activities"),
    search: Optional[str] = Query(None, description="Search in title or description")
):
    """
    Get all activities (public view for all users).
    """
    query = db.query(ActivityModel).options(joinedload(ActivityModel.user))
    query = query.filter(ActivityModel.is_active == True)
    
    if upcoming_only:
        query = query.filter(ActivityModel.date_time >= datetime.now())
    
    if search:
        query = query.filter(
            (ActivityModel.title.ilike(f'%{search}%')) |
            (ActivityModel.description.ilike(f'%{search}%'))
        )
    
    query = query.order_by(ActivityModel.date_time.asc())
    return query.all()

@router.get("/{activity_id}", response_model=ActivitySchema)
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

@router.put("/{activity_id}", response_model=ActivitySchema)
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
    
    db_activity = db.query(ActivityModel).filter(ActivityModel.id == activity_id).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with id {activity_id} not found"
        )
    
    update_data = activity_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_activity, key, value)
    
    db.commit()
    db.refresh(db_activity)
    return db_activity

# In your activities controller

# Change DELETE endpoint to do HARD DELETE (permanent removal)
@router.delete("/{activity_id}")
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Permanently delete an activity - ADMIN ONLY.
    WARNING: This will permanently remove the activity from the database.
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
    
    # Permanently delete from database
    db.delete(db_activity)
    db.commit()
    
    return {"message": f"Activity with id {activity_id} has been permanently deleted"}

# Keep the toggle endpoint for activate/deactivate
@router.patch("/{activity_id}/toggle")
def toggle_activity_status(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Toggle activity status (active/inactive) - ADMIN ONLY.
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
    
    db_activity.is_active = not db_activity.is_active
    db.commit()
    
    status_word = "activated" if db_activity.is_active else "deactivated"
    return db_activity  # Return the updated activity
    
@router.get("/admin/all", response_model=List[ActivitySchema])
def get_all_activities_admin(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get all activities for admin dashboard (including inactive ones).
    ADMIN ONLY.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can view all activities"
        )
    
    activities = db.query(ActivityModel).\
        options(joinedload(ActivityModel.user)).\
        order_by(ActivityModel.created_at.desc()).\
        all()
    
    return activities

@router.post("/upload-image")
def upload_activity_image(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Upload an image for activity - ADMIN ONLY.
    Returns the uploaded image URL.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can upload images"
        )
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    try:
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET")
        )
        
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="farmventure/activities",
            resource_type="image"
        )
        
        return {"image_url": upload_result.get("secure_url")}  
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )