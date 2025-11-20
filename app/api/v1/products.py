"""
Products API endpoints for inventory management.
"""
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.stock import StockTransaction
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ProductBulkCreate,
    ProductBulkCreateResponse
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product.

    - **sku**: Unique product SKU (per user)
    - **name**: Product name
    - **current_stock**: Initial stock quantity
    - **critical_stock_level**: Alert threshold
    """
    # Check if SKU already exists for this user
    result = await db.execute(
        select(Product).where(
            and_(
                Product.user_id == current_user.id,
                Product.sku == product_data.sku
            )
        )
    )
    existing_product = result.scalar_one_or_none()

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product_data.sku}' already exists"
        )

    # Create product
    new_product = Product(
        user_id=current_user.id,
        **product_data.model_dump(exclude={'metadata_'})
    )

    if product_data.metadata_:
        new_product.metadata_ = product_data.metadata_

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    # Create initial stock transaction if stock > 0
    if product_data.current_stock > 0:
        transaction = StockTransaction(
            user_id=current_user.id,
            product_id=new_product.id,
            created_by=current_user.id,
            transaction_type="in",
            quantity=product_data.current_stock,
            reference_type="manual",
            notes="Initial stock"
        )
        db.add(transaction)
        await db.commit()

    return new_product


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    low_stock_only: bool = False,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List products with pagination and filtering.

    - **page**: Page number (starts at 1)
    - **page_size**: Items per page (max 100)
    - **search**: Search by name or SKU
    - **category**: Filter by category
    - **low_stock_only**: Show only low stock items
    - **active_only**: Show only active products
    """
    # Build query
    query = select(Product).where(Product.user_id == current_user.id)

    if active_only:
        query = query.where(Product.is_active == True)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.sku.ilike(search_pattern),
                Product.barcode_gtin.ilike(search_pattern)
            )
        )

    if category:
        query = query.where(Product.category == category)

    if low_stock_only:
        query = query.where(Product.current_stock <= Product.critical_stock_level)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Product.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/low-stock", response_model=ProductListResponse)
async def get_low_stock_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get products with low stock levels.
    """
    query = select(Product).where(
        and_(
            Product.user_id == current_user.id,
            Product.is_active == True,
            Product.current_stock <= Product.critical_stock_level
        )
    ).order_by(Product.current_stock.asc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific product by ID."""
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    product_data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a product.

    Only provided fields will be updated.
    """
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Update fields
    update_data = product_data.model_dump(exclude_unset=True, exclude={'metadata_'})
    for field, value in update_data.items():
        setattr(product, field, value)

    if product_data.metadata_ is not None:
        product.metadata_ = product_data.metadata_

    await db.commit()
    await db.refresh(product)

    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product (soft delete - sets is_active to False).
    """
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    product.is_active = False
    await db.commit()

    return None


@router.post("/bulk", response_model=ProductBulkCreateResponse)
async def bulk_create_products(
    bulk_data: ProductBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk create products from a list.

    Returns count of created and failed products.
    """
    created = 0
    failed = 0
    errors = []

    for idx, product_data in enumerate(bulk_data.products):
        try:
            # Check if SKU exists
            result = await db.execute(
                select(Product).where(
                    and_(
                        Product.user_id == current_user.id,
                        Product.sku == product_data.sku
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                failed += 1
                errors.append({
                    "index": idx,
                    "sku": product_data.sku,
                    "error": "SKU already exists"
                })
                continue

            # Create product
            new_product = Product(
                user_id=current_user.id,
                **product_data.model_dump(exclude={'metadata_'})
            )

            if product_data.metadata_:
                new_product.metadata_ = product_data.metadata_

            db.add(new_product)
            created += 1

        except Exception as e:
            failed += 1
            errors.append({
                "index": idx,
                "sku": product_data.sku,
                "error": str(e)
            })

    if created > 0:
        await db.commit()

    return ProductBulkCreateResponse(
        created=created,
        failed=failed,
        errors=errors if errors else None
    )
