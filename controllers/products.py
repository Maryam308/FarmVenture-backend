from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models.product import ProductModel
from models.user import UserModel, UserRole
from serializers.product import ProductCreate, ProductUpdate, ProductSchema
from database import get_db
from dependencies.get_current_user import get_current_user

router = APIRouter()

# GET all products (public - no auth required)
@router.get('/products', response_model=List[ProductSchema])
def get_products(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    limit: int = Query(20, ge=1, le=100, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get all products with optional filtering and search.
    
    - **category**: Filter by product category
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter  
    - **search**: Search term in name and description
    - **limit**: Number of results per page (1-100)
    - **offset**: Pagination offset
    
    Returns all active products ordered by newest first.
    """
    query = db.query(ProductModel).filter(ProductModel.is_active == True)
    
    # Apply filters
    if category:
        query = query.filter(ProductModel.category == category)
    if min_price:
        query = query.filter(ProductModel.price >= min_price)
    if max_price:
        query = query.filter(ProductModel.price <= max_price)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (ProductModel.name.ilike(search_term)) | 
            (ProductModel.description.ilike(search_term))
        )
    
    # Order by creation date (newest first) and apply pagination
    products = query.order_by(ProductModel.created_at.desc())\
                   .limit(limit)\
                   .offset(offset)\
                   .all()
    
    return products

# GET single product (public endpoint)
@router.get('/products/{product_id}', response_model=ProductSchema)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Get a single product by ID.
    
    Returns product details with user information.
    """
    product = db.query(ProductModel).filter(
        ProductModel.id == product_id,
        ProductModel.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    return product

# POST create product (requires authentication)
@router.post('/products', response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new product.
    
    - **name**: Product name (1-100 characters)
    - **description**: Product description
    - **price**: Product price (must be positive)
    - **category**: Product category
    
    Requires authentication. The authenticated user becomes the product owner.
    """
    new_product = ProductModel(
        name=product.name,
        description=product.description,
        price=product.price,
        category=product.category,
        # image_url=product.image_url,  # TODO: Uncomment for Cloudinary
        user_id=current_user.id  # Authenticated user is the owner
    )
    
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return new_product

# PUT update product (requires authentication - owner OR admin)
@router.put('/products/{product_id}', response_model=ProductSchema)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update a product.
    
    Only the product owner or an admin can update a product.
    All fields are optional - only provided fields will be updated.
    """
    db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    # Authorization: product owner OR admin can update
    if db_product.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this product"
        )
    
    # Update only provided fields
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

# DELETE product (requires authentication - owner OR admin)
@router.delete('/products/{product_id}')
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete a product (soft delete).
    
    Only the product owner or an admin can delete a product.
    This performs a soft delete by setting is_active=False.
    """
    db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    # Authorization: product owner OR admin can delete
    if db_product.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this product"
        )
    
    # Soft delete (set is_active=False instead of actual deletion)
    db_product.is_active = False
    db.commit()
    
    return {"message": f"Product with id {product_id} has been deleted successfully"}

# GET products by user (public endpoint)
@router.get('/users/{user_id}/products', response_model=List[ProductSchema])
def get_user_products(
    user_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get all products by a specific user.
    
    Returns active products created by the specified user.
    """
    products = db.query(ProductModel).filter(
        ProductModel.user_id == user_id,
        ProductModel.is_active == True
    ).order_by(ProductModel.created_at.desc())\
     .limit(limit)\
     .offset(offset)\
     .all()
    
    return products

# GET all products including inactive (admin only)
@router.get('/admin/products', response_model=List[ProductSchema])
def get_all_products_admin(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    show_inactive: bool = Query(False, description="Include inactive products"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get all products (including inactive) - Admin only.
    
    Only users with ADMIN role can access this endpoint.
    """
    # Authorization: only admin can access
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    query = db.query(ProductModel)
    
    # Filter out inactive products unless explicitly requested
    if not show_inactive:
        query = query.filter(ProductModel.is_active == True)
    
    products = query.order_by(ProductModel.created_at.desc())\
                   .limit(limit)\
                   .offset(offset)\
                   .all()
    
    return products

# RESTORE deleted product (admin only)
@router.put('/admin/products/{product_id}/restore', response_model=ProductSchema)
def restore_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Restore a soft-deleted product - Admin only.
    
    Only users with ADMIN role can restore deleted products.
    """
    # Authorization: only admin can restore
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    # Restore the product
    db_product.is_active = True
    db.commit()
    db.refresh(db_product)
    
    return db_product