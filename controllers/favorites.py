from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from models.favorite import FavoriteModel
from models.product import ProductModel
from models.activity import ActivityModel
from models.user import UserModel
from serializers.favorite import FavoriteCreate, FavoriteResponse
from serializers.product import ProductSchema
from serializers.activity import ActivitySchema
from database import get_db
from dependencies.get_current_user import get_current_user

router = APIRouter()

@router.post('/favorites', response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def add_favorite(
    favorite: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Add a product or activity to user's favorites.
    
    - **item_id**: ID of the product or activity to favorite
    - **item_type**: Type of item ('product' or 'activity')
    """
    # Validate item_type
    if favorite.item_type not in ['product', 'activity']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_type must be either 'product' or 'activity'"
        )
    
    # Check if item exists and is active
    if favorite.item_type == 'product':
        item = db.query(ProductModel).filter(
            ProductModel.id == favorite.item_id,
            ProductModel.is_active == True
        ).first()
    else:  # activity
        item = db.query(ActivityModel).filter(
            ActivityModel.id == favorite.item_id,
            ActivityModel.is_active == True
        ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{favorite.item_type.capitalize()} with id {favorite.item_id} not found or is inactive"
        )
    
    # Check if already favorited
    existing_favorite = db.query(FavoriteModel).filter(
        FavoriteModel.user_id == current_user.id,
        FavoriteModel.item_id == favorite.item_id,
        FavoriteModel.item_type == favorite.item_type
    ).first()
    
    if existing_favorite:
        # Instead of error, just return the existing favorite
        return existing_favorite
    
    # Create new favorite
    new_favorite = FavoriteModel(
        user_id=current_user.id,
        item_id=favorite.item_id,
        item_type=favorite.item_type
    )
    
    db.add(new_favorite)
    db.commit()
    db.refresh(new_favorite)
    
    return new_favorite


@router.get('/favorites', response_model=List[dict])
def get_user_favorites(
    item_type: str = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get all favorites for the current user with details.
    
    - **item_type**: Optional filter for 'product' or 'activity'
    
    Returns favorites for active items only.
    """
    query = db.query(FavoriteModel).filter(
        FavoriteModel.user_id == current_user.id
    )
    
    if item_type:
        if item_type not in ['product', 'activity']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="item_type must be either 'product' or 'activity'"
            )
        query = query.filter(FavoriteModel.item_type == item_type)
    
    favorites = query.all()
    
    # Fetch details for each favorite
    result = []
    for fav in favorites:
        if fav.item_type == 'product':
            item = db.query(ProductModel).filter(
                ProductModel.id == fav.item_id,
                ProductModel.is_active == True
            ).first()
            if item:
                result.append({
                    'id': fav.id,
                    'user_id': fav.user_id,
                    'item_id': fav.item_id,
                    'item_type': fav.item_type,
                    'created_at': fav.created_at,
                    'item': ProductSchema.from_orm(item).dict()
                })
        else:  # activity
            item = db.query(ActivityModel).filter(
                ActivityModel.id == fav.item_id,
                ActivityModel.is_active == True
            ).first()
            if item:
                result.append({
                    'id': fav.id,
                    'user_id': fav.user_id,
                    'item_id': fav.item_id,
                    'item_type': fav.item_type,
                    'created_at': fav.created_at,
                    'item': ActivitySchema.from_orm(item).dict()
                })
    
    return result


@router.get('/favorites/ids', response_model=dict)
def get_favorite_ids(
    item_type: str = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get just the IDs of favorited items (lightweight endpoint for checking favorites).
    
    - **item_type**: Optional filter for 'product' or 'activity'
    
    Returns a dict with item_type as key and list of IDs as value.
    """
    query = db.query(FavoriteModel).filter(
        FavoriteModel.user_id == current_user.id
    )
    
    if item_type:
        if item_type not in ['product', 'activity']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="item_type must be either 'product' or 'activity'"
            )
        query = query.filter(FavoriteModel.item_type == item_type)
    
    favorites = query.all()
    
    # Group by item_type
    result = {
        'products': [],
        'activities': []
    }
    
    for fav in favorites:
        if fav.item_type == 'product':
            result['products'].append(fav.item_id)
        else:
            result['activities'].append(fav.item_id)
    
    return result


@router.delete('/favorites/{item_type}/{item_id}')
def remove_favorite(
    item_type: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Remove an item from user's favorites.
    
    - **item_type**: Type of item ('product' or 'activity')
    - **item_id**: ID of the item to unfavorite
    """
    if item_type not in ['product', 'activity']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_type must be either 'product' or 'activity'"
        )
    
    favorite = db.query(FavoriteModel).filter(
        FavoriteModel.user_id == current_user.id,
        FavoriteModel.item_id == item_id,
        FavoriteModel.item_type == item_type
    ).first()
    
    if not favorite:
        # Return success even if not found (idempotent operation)
        return {"message": f"{item_type.capitalize()} {item_id} was not in favorites", "success": True}
    
    db.delete(favorite)
    db.commit()
    
    return {"message": f"{item_type.capitalize()} {item_id} removed from favorites", "success": True}


@router.get('/favorites/check/{item_type}/{item_id}', response_model=dict)
def check_favorite(
    item_type: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Check if an item is in user's favorites.
    
    - **item_type**: Type of item ('product' or 'activity')
    - **item_id**: ID of the item to check
    """
    if item_type not in ['product', 'activity']:
        return {"is_favorited": False}
    
    favorite = db.query(FavoriteModel).filter(
        FavoriteModel.user_id == current_user.id,
        FavoriteModel.item_id == item_id,
        FavoriteModel.item_type == item_type
    ).first()
    
    return {"is_favorited": favorite is not None}