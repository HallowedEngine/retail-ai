"""
Alerts API endpoints for notifications and warnings.
"""
from typing import Optional
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.alert import Alert
from app.models.product import Product
from app.schemas.alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertWithProduct,
    AlertListResponse,
    AlertStats,
    AlertType,
    AlertSeverity
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alert.

    - **alert_type**: Type of alert (low_stock, out_of_stock, expiry_warning, system)
    - **severity**: Severity level (low, medium, high, critical)
    - **title**: Alert title
    - **message**: Detailed message
    """
    # Verify product exists if product_id is provided
    if alert_data.product_id:
        result = await db.execute(
            select(Product).where(
                and_(
                    Product.id == alert_data.product_id,
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

    # Create alert
    new_alert = Alert(
        user_id=current_user.id,
        **alert_data.model_dump(exclude={'metadata_'})
    )

    if alert_data.metadata_:
        new_alert.metadata_ = alert_data.metadata_

    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)

    return new_alert


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    alert_type: Optional[AlertType] = None,
    severity: Optional[AlertSeverity] = None,
    product_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List alerts with filtering.

    - **unread_only**: Show only unread alerts
    - **alert_type**: Filter by alert type
    - **severity**: Filter by severity
    - **product_id**: Filter by product
    """
    # Build query
    query = select(Alert).where(Alert.user_id == current_user.id)

    if unread_only:
        query = query.where(Alert.is_read == False)

    if alert_type:
        query = query.where(Alert.alert_type == alert_type.value)

    if severity:
        query = query.where(Alert.severity == severity.value)

    if product_id:
        query = query.where(Alert.product_id == product_id)

    # Filter out expired alerts
    query = query.where(
        or_(
            Alert.expires_at.is_(None),
            Alert.expires_at > datetime.utcnow()
        )
    )

    # Get total and unread count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    unread_query = select(func.count()).where(
        and_(
            Alert.user_id == current_user.id,
            Alert.is_read == False,
            or_(
                Alert.expires_at.is_(None),
                Alert.expires_at > datetime.utcnow()
            )
        )
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar()

    # Get paginated results
    query = query.order_by(desc(Alert.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        items=alerts,
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific alert by ID."""
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.user_id == current_user.id
            )
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    return alert


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: uuid.UUID,
    alert_data: AlertUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an alert (typically to mark as read).

    - **is_read**: Mark alert as read/unread
    """
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.user_id == current_user.id
            )
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    # Update fields
    update_data = alert_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    await db.commit()
    await db.refresh(alert)

    return alert


@router.post("/{alert_id}/read", response_model=AlertResponse)
async def mark_alert_read(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark an alert as read."""
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.user_id == current_user.id
            )
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    alert.is_read = True
    await db.commit()
    await db.refresh(alert)

    return alert


@router.post("/mark-all-read", status_code=status.HTTP_200_OK)
async def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all unread alerts as read."""
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.user_id == current_user.id,
                Alert.is_read == False
            )
        )
    )
    alerts = result.scalars().all()

    for alert in alerts:
        alert.is_read = True

    await db.commit()

    return {"message": f"Marked {len(alerts)} alerts as read"}


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an alert."""
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.user_id == current_user.id
            )
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    await db.delete(alert)
    await db.commit()

    return None


@router.get("/stats/summary", response_model=AlertStats)
async def get_alert_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert statistics.

    Returns counts by severity, type, and recent activity.
    """
    # Total alerts (non-expired)
    total_result = await db.execute(
        select(func.count()).where(
            and_(
                Alert.user_id == current_user.id,
                or_(
                    Alert.expires_at.is_(None),
                    Alert.expires_at > datetime.utcnow()
                )
            )
        )
    )
    total = total_result.scalar() or 0

    # Unread count
    unread_result = await db.execute(
        select(func.count()).where(
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
    unread = unread_result.scalar() or 0

    # By severity
    by_severity = {}
    for severity in ['low', 'medium', 'high', 'critical']:
        count_result = await db.execute(
            select(func.count()).where(
                and_(
                    Alert.user_id == current_user.id,
                    Alert.severity == severity,
                    or_(
                        Alert.expires_at.is_(None),
                        Alert.expires_at > datetime.utcnow()
                    )
                )
            )
        )
        by_severity[severity] = count_result.scalar() or 0

    # By type
    by_type = {}
    for alert_type in ['low_stock', 'out_of_stock', 'expiry_warning', 'system']:
        count_result = await db.execute(
            select(func.count()).where(
                and_(
                    Alert.user_id == current_user.id,
                    Alert.alert_type == alert_type,
                    or_(
                        Alert.expires_at.is_(None),
                        Alert.expires_at > datetime.utcnow()
                    )
                )
            )
        )
        by_type[alert_type] = count_result.scalar() or 0

    # Recent count (last 24 hours)
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_result = await db.execute(
        select(func.count()).where(
            and_(
                Alert.user_id == current_user.id,
                Alert.created_at >= yesterday
            )
        )
    )
    recent_count = recent_result.scalar() or 0

    return AlertStats(
        total=total,
        unread=unread,
        by_severity=by_severity,
        by_type=by_type,
        recent_count=recent_count
    )
