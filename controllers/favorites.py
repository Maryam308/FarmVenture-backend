from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from models.favorite import FavoriteModel
from models.product import ProductModel
from models.activity import ActivityModel
from models.user import UserModel, UserRole
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
    print("=" * 50)
    print("ADD FAVORITE - DEBUG INFO")
    print(f"User ID: {current_user.id}")
    print(f"User Role Type: {type(current_user.role)}")
    print(f"User Role Value: {current_user.role}")
    print(f"Has is_customer method: {hasattr(current_user, 'is_customer')}")
    
    try:
        result = current_user.is_customer()
        print(f"is_customer() returned: {result}")
    except Exception as e:
        print(f"ERROR calling is_customer(): {e}")
        raise
    
    print("=" * 50)
    
    if not current_user.is_customer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can add favorites"
        )
    
    if favorite.item_type not in ['product', 'activity']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_type must be either 'product' or 'activity'"
        )
    
    if favorite.item_type == 'product':
        item = db.query(ProductModel).filter(
            ProductModel.id == favorite.item_id,
            ProductModel.is_active == True
        ).first()
    else:
        item = db.query(ActivityModel).filter(
            ActivityModel.id == favorite.item_id,
            ActivityModel.is_active == True
        ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{favorite.item_type.capitalize()} with id {favorite.item_id} not found or is inactive"
        )
    
    existing_favorite = db.query(FavoriteModel).filter(
        FavoriteModel.user_id == current_user.id,
        FavoriteModel.item_id == favorite.item_id,
        FavoriteModel.item_type == favorite.item_type
    ).first()
    
    if existing_favorite:
        return existing_favorite
    
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
    print("=" * 50)
    print("GET FAVORITES - DEBUG INFO")
    print(f"User ID: {current_user.id}")
    print(f"User Role Type: {type(current_user.role)}")
    print(f"User Role Value: {current_user.role}")
    print(f"Has is_customer method: {hasattr(current_user, 'is_customer')}")
    
    try:
        result = current_user.is_customer()
        print(f"is_customer() returned: {result}")
    except Exception as e:
        print(f"ERROR calling is_customer(): {e}")
        raise
    
    print("=" * 50)
    
    if not current_user.is_customer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can view favorites"
        )
    
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
    
    result = []
    for fav in favorites:
        if fav.item_type == 'product':
            item = db.query(ProductModel).filter(
                ProductModel.id == fav.item_id,
                ProductModel.is_active == True
            ).options(joinedload(ProductModel.user)).first()
            
            if item:
                result.append({
                    'id': fav.id,
                    'user_id': fav.user_id,
                    'item_id': fav.item_id,
                    'item_type': fav.item_type,
                    'created_at': fav.created_at,
                    'item': ProductSchema.from_orm(item).dict()
                })
        else:
            item = db.query(ActivityModel).filter(
                ActivityModel.id == fav.item_id,
                ActivityModel.is_active == True
            ).options(joinedload(ActivityModel.user)).first()
            
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
    print("=" * 50)
    print("GET FAVORITE IDS - DEBUG INFO")
    print(f"User ID: {current_user.id}")
    print(f"User Role Type: {type(current_user.role)}")
    print(f"User Role Value: {current_user.role}")
    print(f"Has is_customer method: {hasattr(current_user, 'is_customer')}")
    
    try:
        result = current_user.is_customer()
        print(f"is_customer() returned: {result}")
    except Exception as e:
        print(f"ERROR calling is_customer(): {e}")
    
    print("=" * 50)
    
    if not current_user.is_customer():
        return {
            'products': [],
            'activities': []
        }
    
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
    if not current_user.is_customer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can remove favorites"
        )
    
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
    if not current_user.is_customer():
        return {"is_favorited": False}
    
    if item_type not in ['product', 'activity']:
        return {"is_favorited": False}
    
    favorite = db.query(FavoriteModel).filter(
        FavoriteModel.user_id == current_user.id,
        FavoriteModel.item_id == item_id,
        FavoriteModel.item_type == item_type
    ).first()
    
    return {"is_favorited": favorite is not None}