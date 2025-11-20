"""
Dashboard API endpoints for summary statistics and metrics.
"""
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from decimal import Decimal

from app.core.database import get_db, check_db_connection
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.product import Product
from app.models.receipt import Receipt
from app.models.stock import StockTransaction
from app.models.alert import Alert
from app.schemas.dashboard import (
    DashboardSummary,
    HealthCheck,
    RecentActivity,
    DashboardRecent,
    StockTrendData,
    CategoryDistribution
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive dashboard summary with all key metrics.

    Returns product counts, stock info, alerts, receipts, and transaction stats.
    """
    # Product metrics
    total_products_result = await db.execute(
        select(func.count(Product.id)).where(Product.user_id == current_user.id)
    )
    total_products = total_products_result.scalar() or 0

    active_products_result = await db.execute(
        select(func.count(Product.id)).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True
            )
        )
    )
    active_products = active_products_result.scalar() or 0

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
    low_stock_products = low_stock_result.scalar() or 0

    out_of_stock_result = await db.execute(
        select(func.count(Product.id)).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True,
                Product.current_stock == 0
            )
        )
    )
    out_of_stock_products = out_of_stock_result.scalar() or 0

    # Stock value
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

    # Total stock items
    total_stock_result = await db.execute(
        select(func.sum(Product.current_stock)).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True
            )
        )
    )
    total_stock_items = total_stock_result.scalar() or 0

    # Alert metrics
    total_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(
            and_(
                Alert.user_id == current_user.id,
                or_(
                    Alert.expires_at.is_(None),
                    Alert.expires_at > datetime.utcnow()
                )
            )
        )
    )
    total_alerts = total_alerts_result.scalar() or 0

    unread_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(
            and_(
                Alert.user_id == current_user.id,
                Alert.is_read == False,
                or_(
                    Alert.expires_at.is_(None),
                    Alert.expires_at > datetime.utcnow()
                )
            )
        )
    )
    unread_alerts = unread_alerts_result.scalar() or 0

    critical_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(
            and_(
                Alert.user_id == current_user.id,
                Alert.severity == 'critical',
                Alert.is_read == False,
                or_(
                    Alert.expires_at.is_(None),
                    Alert.expires_at > datetime.utcnow()
                )
            )
        )
    )
    critical_alerts = critical_alerts_result.scalar() or 0

    # Receipt metrics
    total_receipts_result = await db.execute(
        select(func.count(Receipt.id)).where(Receipt.user_id == current_user.id)
    )
    total_receipts = total_receipts_result.scalar() or 0

    pending_receipts_result = await db.execute(
        select(func.count(Receipt.id)).where(
            and_(
                Receipt.user_id == current_user.id,
                Receipt.processing_status.in_(['pending', 'processing'])
            )
        )
    )
    pending_receipts = pending_receipts_result.scalar() or 0

    # Receipts today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    receipts_today_result = await db.execute(
        select(func.count(Receipt.id)).where(
            and_(
                Receipt.user_id == current_user.id,
                Receipt.created_at >= today_start
            )
        )
    )
    receipts_today = receipts_today_result.scalar() or 0

    # Transaction metrics
    transactions_today_result = await db.execute(
        select(func.count(StockTransaction.id)).where(
            and_(
                StockTransaction.user_id == current_user.id,
                StockTransaction.created_at >= today_start
            )
        )
    )
    transactions_today = transactions_today_result.scalar() or 0

    week_start = datetime.utcnow() - timedelta(days=7)
    transactions_week_result = await db.execute(
        select(func.count(StockTransaction.id)).where(
            and_(
                StockTransaction.user_id == current_user.id,
                StockTransaction.created_at >= week_start
            )
        )
    )
    transactions_this_week = transactions_week_result.scalar() or 0

    return DashboardSummary(
        total_products=total_products,
        active_products=active_products,
        low_stock_products=low_stock_products,
        out_of_stock_products=out_of_stock_products,
        total_stock_value=total_stock_value,
        total_stock_items=total_stock_items,
        total_alerts=total_alerts,
        unread_alerts=unread_alerts,
        critical_alerts=critical_alerts,
        total_receipts=total_receipts,
        pending_receipts=pending_receipts,
        receipts_today=receipts_today,
        transactions_today=transactions_today,
        transactions_this_week=transactions_this_week,
        last_updated=datetime.utcnow()
    )


@router.get("/recent-activity", response_model=DashboardRecent)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activities across the system.

    Combines recent alerts, receipts, and stock transactions.
    """
    activities: List[RecentActivity] = []

    # Recent alerts (last 5)
    alerts_result = await db.execute(
        select(Alert).where(
            Alert.user_id == current_user.id
        ).order_by(desc(Alert.created_at)).limit(5)
    )
    alerts = alerts_result.scalars().all()

    for alert in alerts:
        activities.append(RecentActivity(
            type="alert",
            title=alert.title,
            description=alert.message,
            timestamp=alert.created_at,
            severity=alert.severity
        ))

    # Recent receipts (last 5)
    receipts_result = await db.execute(
        select(Receipt).where(
            Receipt.user_id == current_user.id
        ).order_by(desc(Receipt.created_at)).limit(5)
    )
    receipts = receipts_result.scalars().all()

    for receipt in receipts:
        activities.append(RecentActivity(
            type="receipt",
            title=f"Receipt #{receipt.receipt_number or 'N/A'}",
            description=f"Store: {receipt.store_name or 'Unknown'} - Status: {receipt.processing_status}",
            timestamp=receipt.created_at
        ))

    # Recent stock transactions (last 5)
    transactions_result = await db.execute(
        select(StockTransaction).where(
            StockTransaction.user_id == current_user.id
        ).order_by(desc(StockTransaction.created_at)).limit(5)
    )
    transactions = transactions_result.scalars().all()

    for transaction in transactions:
        qty_str = f"+{transaction.quantity}" if transaction.quantity > 0 else str(transaction.quantity)
        activities.append(RecentActivity(
            type="stock",
            title=f"Stock {transaction.transaction_type}",
            description=f"Quantity: {qty_str}",
            timestamp=transaction.created_at
        ))

    # Sort all activities by timestamp and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    activities = activities[:limit]

    return DashboardRecent(
        activities=activities,
        total=len(activities)
    )


@router.get("/stock-trend", response_model=List[StockTrendData])
async def get_stock_trend(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get stock trend data for the last N days.

    Returns daily stock movements (in/out) and total stock.
    """
    trend_data = []

    for i in range(days):
        date = datetime.utcnow() - timedelta(days=days - i - 1)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)

        # Stock IN
        stock_in_result = await db.execute(
            select(func.sum(StockTransaction.quantity)).where(
                and_(
                    StockTransaction.user_id == current_user.id,
                    StockTransaction.created_at >= date_start,
                    StockTransaction.created_at < date_end,
                    StockTransaction.quantity > 0
                )
            )
        )
        stock_in = stock_in_result.scalar() or 0

        # Stock OUT
        stock_out_result = await db.execute(
            select(func.sum(StockTransaction.quantity)).where(
                and_(
                    StockTransaction.user_id == current_user.id,
                    StockTransaction.created_at >= date_start,
                    StockTransaction.created_at < date_end,
                    StockTransaction.quantity < 0
                )
            )
        )
        stock_out = abs(stock_out_result.scalar() or 0)

        # Total stock at end of day
        total_stock_result = await db.execute(
            select(func.sum(Product.current_stock)).where(
                and_(
                    Product.user_id == current_user.id,
                    Product.is_active == True
                )
            )
        )
        total_stock = total_stock_result.scalar() or 0

        trend_data.append(StockTrendData(
            date=date_start.strftime('%Y-%m-%d'),
            total_stock=total_stock,
            stock_in=stock_in,
            stock_out=stock_out,
            stock_value=None
        ))

    return trend_data


@router.get("/category-distribution", response_model=List[CategoryDistribution])
async def get_category_distribution(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get product distribution by category.

    Returns product count and stock value per category.
    """
    # Get all products with categories
    result = await db.execute(
        select(Product).where(
            and_(
                Product.user_id == current_user.id,
                Product.is_active == True,
                Product.category.isnot(None)
            )
        )
    )
    products = result.scalars().all()

    # Group by category
    categories = {}
    total_products = len(products)

    for product in products:
        category = product.category or "Uncategorized"

        if category not in categories:
            categories[category] = {
                'count': 0,
                'stock_value': Decimal('0')
            }

        categories[category]['count'] += 1

        if product.unit_price:
            categories[category]['stock_value'] += Decimal(str(product.current_stock)) * product.unit_price

    # Convert to response format
    distribution = []
    for category, data in categories.items():
        percentage = (data['count'] / total_products * 100) if total_products > 0 else 0

        distribution.append(CategoryDistribution(
            category=category,
            count=data['count'],
            percentage=round(percentage, 2),
            stock_value=data['stock_value']
        ))

    # Sort by count descending
    distribution.sort(key=lambda x: x.count, reverse=True)

    return distribution


@router.get("/health", response_model=HealthCheck)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint for monitoring.

    Returns system status and component health.
    """
    db_healthy = await check_db_connection()

    status = "healthy" if db_healthy else "unhealthy"

    return HealthCheck(
        status=status,
        version=settings.app_version,
        database=db_healthy,
        redis=None,  # TODO: Implement Redis health check
        timestamp=datetime.utcnow()
    )
