from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from models.hoot import HootModel
from models.user import UserModel
from models.comment import CommentModel
from serializers.hoot import HootCreate, HootUpdate, HootSchema
from database import get_db
from dependencies.get_current_user import get_current_user
from sqlalchemy.orm import joinedload

router = APIRouter()

@router.post('/hoots', response_model=HootSchema, status_code=status.HTTP_201_CREATED)
def create_hoot(
    hoot: HootCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new hoot.

    - **title**: The title of the hoot (1-255 characters)
    - **text**: The content of the hoot
    - **category**: Category tag (1-50 characters)

    Requires authentication. The authenticated user becomes the author.
    """
    # Create new hoot instance
    new_hoot = HootModel(
        title=hoot.title,
        text=hoot.text,
        category=hoot.category,
        user_id=current_user.id  # Authenticated user is the author
    )

    # Add to database
    db.add(new_hoot)
    db.commit()
    db.refresh(new_hoot)  # Refresh to get the generated id and created_at

    return new_hoot

@router.get('/hoots', response_model=List[HootSchema])
def get_hoots(db: Session = Depends(get_db)):
    """Get all hoots with eager loading for better performance."""
    hoots = db.query(HootModel).\
        options(
            joinedload(HootModel.user),
            joinedload(HootModel.comments).joinedload(CommentModel.user)
        ).all()
    return hoots


@router.get('/hoots/{hoot_id}', response_model=HootSchema)
def get_single_hoot(hoot_id: int, db: Session = Depends(get_db)):
    """
    Get a single hoot by ID.
    
    Returns the hoot with all associated user and comments data.
    """
    hoot = db.query(HootModel).filter(HootModel.id == hoot_id).first()
    
    if not hoot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hoot with id {hoot_id} not found"
        )
    
    return hoot

@router.put('/hoots/{hoot_id}', response_model=HootSchema)
def update_hoot(
    hoot_id: int,
    hoot_update: HootUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update a hoot.
    
    Only the author can update their hoot.
    All fields are optional - only provided fields will be updated.
    """
    # Find the hoot
    db_hoot = db.query(HootModel).filter(HootModel.id == hoot_id).first()
    
    if not db_hoot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hoot with id {hoot_id} not found"
        )
    
    # Authorization check: only author can update
    if db_hoot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this hoot"
        )
    
    # Update only provided fields
    update_data = hoot_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hoot, key, value)
    
    db.commit()
    db.refresh(db_hoot)
    return db_hoot

@router.delete('/hoots/{hoot_id}')
def delete_hoot(
    hoot_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete a hoot.
    
    Only the author can delete their hoot.
    All associated comments will be deleted automatically (CASCADE).
    """
    db_hoot = db.query(HootModel).filter(HootModel.id == hoot_id).first()
    
    if not db_hoot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hoot with id {hoot_id} not found"
        )
    
    # Authorization check
    if db_hoot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this hoot"
        )
    
    db.delete(db_hoot)
    db.commit()
    
    return {"message": f"Hoot with id {hoot_id} has been deleted successfully"}