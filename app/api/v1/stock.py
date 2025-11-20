"""
Stock Management API endpoints for tracking inventory movements.
"""
from typing import Optional
from datetime import datetime, timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.stock import StockTransaction
from app.schemas.stock import (
    StockTransactionCreate,
    StockAdjustment,
    StockTransactionResponse,
    StockTransactionWithProduct,
    StockTransactionListResponse,
    StockSummary,
    StockStats
)

router = APIRouter(prefix="/stock", tags=["Stock Management"])


@router.post("/transaction", response_model=StockTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_transaction(
    transaction_data: StockTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a stock transaction (in/out/adjustment).

    - **product_id**: Product UUID
    - **transaction_type**: 'in', 'out', or 'adjustment'
    - **quantity**: Positive for IN, negative for OUT
    """
    # Get product
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == transaction_data.product_id,
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

    # Validate quantity based on transaction type
    quantity = transaction_data.quantity

    if transaction_data.transaction_type == "out":
        if quantity > 0:
            quantity = -quantity  # Make it negative

        if product.current_stock + quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {product.current_stock}"
            )

    # Create transaction
    transaction = StockTransaction(
        user_id=current_user.id,
        product_id=product.id,
        created_by=current_user.id,
        **transaction_data.model_dump()
    )

    db.add(transaction)

    # Update product stock
    product.current_stock += quantity

    await db.commit()
    await db.refresh(transaction)

    return transaction


@router.post("/adjust", response_model=StockTransactionResponse)
async def adjust_stock(
    adjustment: StockAdjustment,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually adjust stock to a specific quantity.

    Creates an adjustment transaction with the difference.
    """
    # Get product
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == adjustment.product_id,
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

    # Calculate difference
    difference = adjustment.new_quantity - product.current_stock

    # Create adjustment transaction
    transaction = StockTransaction(
        user_id=current_user.id,
        product_id=product.id,
        created_by=current_user.id,
        transaction_type="adjustment",
        quantity=difference,
        reference_type="manual",
        notes=adjustment.notes or f"Stock adjusted from {product.current_stock} to {adjustment.new_quantity}"
    )

    db.add(transaction)

    # Update product stock
    product.current_stock = adjustment.new_quantity

    await db.commit()
    await db.refresh(transaction)

    return transaction


@router.get("/transactions", response_model=StockTransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    product_id: Optional[uuid.UUID] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List stock transactions with filtering.

    - **product_id**: Filter by product
    - **transaction_type**: Filter by type (in/out/adjustment)
    - **start_date**: Filter from date
    - **end_date**: Filter to date
    """
    # Build query
    query = select(StockTransaction).where(StockTransaction.user_id == current_user.id)

    if product_id:
        query = query.where(StockTransaction.product_id == product_id)

    if transaction_type:
        query = query.where(StockTransaction.transaction_type == transaction_type)

    if start_date:
        query = query.where(StockTransaction.created_at >= start_date)

    if end_date:
        query = query.where(StockTransaction.created_at <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(desc(StockTransaction.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return StockTransactionListResponse(
        items=transactions,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/transactions/{transaction_id}", response_model=StockTransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific stock transaction."""
    result = await db.execute(
        select(StockTransaction).where(
            and_(
                StockTransaction.id == transaction_id,
                StockTransaction.user_id == current_user.id
            )
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return transaction


@router.get("/summary", response_model=StockSummary)
async def get_stock_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get stock summary statistics.

    Returns overview of total products, stock value, low stock items, etc.
    """
    # Total products
    total_products_result = await db.execute(
        select(func.count(Product.id)).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True
            )
        )
    )
    total_products = total_products_result.scalar() or 0

    # Low stock count
    low_stock_result = await db.execute(
        select(func.count(Product.id)).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True,
                Product.current_stock <= Product.critical_stock_level,
                Product.current_stock > 0
            )
        )
    )
    low_stock_count = low_stock_result.scalar() or 0

    # Out of stock count
    out_of_stock_result = await db.execute(
        select(func.count(Product.id)).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True,
                Product.current_stock == 0
            )
        )
    )
    out_of_stock_count = out_of_stock_result.scalar() or 0

    # Total stock value
    stock_value_result = await db.execute(
        select(func.sum(Product.current_stock * Product.unit_price)).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True,
                Product.unit_price.isnot(None)
            )
        )
    )
    total_stock_value = stock_value_result.scalar()

    # Total categories
    categories_result = await db.execute(
        select(func.count(func.distinct(Product.category))).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True,
                Product.category.isnot(None)
            )
        )
    )
    total_categories = categories_result.scalar() or 0

    # Recent transactions (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_transactions_result = await db.execute(
        select(func.count(StockTransaction.id)).where(
            and_(
                StockTransaction.user_id == current_user.id,
                StockTransaction.created_at >= yesterday
            )
        )
    )
    recent_transactions = recent_transactions_result.scalar() or 0

    return StockSummary(
        total_products=total_products,
        total_stock_value=float(total_stock_value) if total_stock_value else None,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        total_categories=total_categories,
        recent_transactions=recent_transactions
    )


@router.get("/stats", response_model=StockStats)
async def get_stock_stats(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get stock statistics for a given period.

    - **days**: Number of days to look back (default 7, max 90)
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get transactions in period
    result = await db.execute(
        select(StockTransaction).where(
            and_(
                StockTransaction.user_id == current_user.id,
                StockTransaction.created_at >= start_date
            )
        )
    )
    transactions = result.scalars().all()

    total_in = sum(t.quantity for t in transactions if t.quantity > 0)
    total_out = abs(sum(t.quantity for t in transactions if t.quantity < 0))
    net_change = total_in - total_out

    return StockStats(
        total_in=total_in,
        total_out=total_out,
        net_change=net_change,
        transactions_count=len(transactions),
        most_active_products=[],  # TODO: Implement if needed
        stock_distribution={}  # TODO: Implement if needed
    )
