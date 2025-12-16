from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from models.product import ProductModel
from models.user import UserModel, UserRole
from serializers.product import ProductCreate, ProductUpdate, ProductSchema
from database import get_db
from dependencies.get_current_user import get_current_user
import cloudinary.uploader
import cloudinary
from dotenv import load_dotenv
import os

load_dotenv()

# Configure Cloudinary 
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

router = APIRouter()

# GET all products (public - no auth required) - Only active products
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
    Get all ACTIVE products with optional filtering and search.
    
    - **category**: Filter by product category
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter  
    - **search**: Search term in name and description
    - **limit**: Number of results per page (1-100)
    - **offset**: Pagination offset
    
    Returns only active products ordered by newest first.
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

# GET single product (public endpoint) - Only active products
@router.get('/products/{product_id}', response_model=ProductSchema)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    - Get a single ACTIVE product by ID.
    
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

# GET any product by ID (including inactive) - for authenticated users
@router.get('/products/{product_id}/any', response_model=ProductSchema)
def get_any_product(
    product_id: int, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get any product by ID (including inactive products).
    - Product owner can view their own inactive products
    - Admin can view any product (active or inactive)
    - Regular users cannot view other users' inactive products
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    # Check permissions
    is_owner = product.user_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN
    
    # If product is active, anyone can view it
    if product.is_active:
        return product
    
    # If product is inactive, only owner or admin can view it
    if not product.is_active and (is_owner or is_admin):
        return product
    
    # If we get here, user is not authorized to view this inactive product
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product with id {product_id} not found"
    )

# Image upload endpoint
@router.post('/products/upload-image', response_model=dict)
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Upload a product image to Cloudinary.
    Returns the image URL.
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed"
        )
    
    try:
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            folder="farmventure/products",
            resource_type="image",
            transformation=[
                {"width": 800, "height": 600, "crop": "limit"},
                {"quality": "auto:good"}
            ]
        )
        
        return {"url": result.get("secure_url")}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )

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
    - **image_url**: Product image URL (optional)
    
    Requires authentication. The authenticated user becomes the product owner.
    By default, new products are created as ACTIVE.
    """
    new_product = ProductModel(
        name=product.name,
        description=product.description,
        price=product.price,
        category=product.category,
        image_url=product.image_url,
        is_active=True,  # New products are active by default
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
    Use is_active field to activate/deactivate product.
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

# DELETE product - HARD DELETE (requires authentication - owner OR admin)
@router.delete('/products/{product_id}')
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    DELETE a product permanently (hard delete).
    
    Only the product owner or an admin can delete a product.
    This performs a HARD DELETE - product is removed from database entirely.
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
    
    # HARD DELETE - remove from database
    db.delete(db_product)
    db.commit()
    
    return {"message": f"Product with id {product_id} has been permanently deleted"}

# GET products by user (public endpoint) - Only active products
@router.get('/users/{user_id}/products', response_model=List[ProductSchema])
def get_user_products(
    user_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get all ACTIVE products by a specific user.
    
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

# GET all products by user (including inactive) - for profile page
@router.get('/users/{user_id}/all-products', response_model=List[ProductSchema])
def get_all_user_products(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get ALL products by a specific user (including inactive).
    
    Only the user themselves or an admin can access inactive products.
    """
    # Check if user is accessing their own products or is admin
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these products"
        )
    
    products = db.query(ProductModel).filter(
        ProductModel.user_id == user_id
    ).order_by(ProductModel.created_at.desc()).all()
    
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

# ACTIVATE/DEACTIVATE product (admin only)
@router.put('/admin/products/{product_id}/toggle-active', response_model=ProductSchema)
def toggle_product_active(
    product_id: int,
    is_active: bool = Query(..., description="Set product active status"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Toggle product active status - Admin only.
    
    Only users with ADMIN role can change product active status.
    """
    # Authorization: only admin can access
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
    
    # Toggle active status
    db_product.is_active = is_active
    db.commit()
    db.refresh(db_product)
    
    return db_product