"""
Receipts API endpoints for invoice/receipt processing with OCR.
"""
from typing import Optional
import uuid
import os
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.receipt import Receipt, ReceiptItem
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptUpdate,
    ReceiptResponse,
    ReceiptWithItems,
    ReceiptListResponse,
    ReceiptUploadResponse,
    ReceiptProcessingStatus,
    ReceiptItemResponse,
    ReceiptItemCreate,
    ReceiptItemUpdate
)

router = APIRouter(prefix="/receipts", tags=["Receipts"])


async def save_upload_file(file: UploadFile) -> tuple[str, str]:
    """
    Save uploaded file and return file path and hash.

    Returns:
        tuple: (file_path, file_hash)
    """
    # Create upload directory if it doesn't exist
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Read file content
    content = await file.read()

    # Calculate hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Generate filename
    extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{file_hash}.{extension}"
    file_path = os.path.join(settings.upload_dir, filename)

    # Save file
    with open(file_path, 'wb') as f:
        f.write(content)

    return file_path, file_hash


@router.post("/upload", response_model=ReceiptUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: UploadFile = File(...),
    store_name: Optional[str] = Form(None),
    receipt_date: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a receipt image for OCR processing.

    - **file**: Receipt image (JPG, PNG, PDF)
    - **store_name**: Optional store name
    - **receipt_date**: Optional receipt date (YYYY-MM-DD)

    Returns receipt ID and processing status.
    """
    # Validate file type
    if file.content_type not in ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, PNG, and PDF files are allowed"
        )

    # Save file
    try:
        file_path, file_hash = await save_upload_file(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Check if receipt with same hash already exists
    result = await db.execute(
        select(Receipt).where(
            and_(
                Receipt.user_id == current_user.id,
                Receipt.image_hash == file_hash
            )
        )
    )
    existing_receipt = result.scalar_one_or_none()

    if existing_receipt:
        return ReceiptUploadResponse(
            receipt_id=existing_receipt.id,
            status="duplicate",
            message="Receipt already exists",
            confidence=existing_receipt.ocr_confidence
        )

    # Create receipt record
    new_receipt = Receipt(
        user_id=current_user.id,
        image_url=file_path,
        image_hash=file_hash,
        store_name=store_name,
        processing_status="pending"
    )

    db.add(new_receipt)
    await db.commit()
    await db.refresh(new_receipt)

    # TODO: Trigger OCR processing task (Celery)
    # For now, just return the receipt

    return ReceiptUploadResponse(
        receipt_id=new_receipt.id,
        status="pending",
        message="Receipt uploaded successfully. Processing will start shortly.",
        confidence=None
    )


@router.get("", response_model=ReceiptListResponse)
async def list_receipts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = None,
    store_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List receipts with pagination and filtering.

    - **status_filter**: Filter by processing status
    - **store_name**: Filter by store name
    """
    # Build query
    query = select(Receipt).where(Receipt.user_id == current_user.id)

    if status_filter:
        query = query.where(Receipt.processing_status == status_filter)

    if store_name:
        query = query.where(Receipt.store_name.ilike(f"%{store_name}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(desc(Receipt.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    receipts = result.scalars().all()

    return ReceiptListResponse(
        items=receipts,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/{receipt_id}", response_model=ReceiptWithItems)
async def get_receipt(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific receipt with its items."""
    result = await db.execute(
        select(Receipt).where(
            and_(
                Receipt.id == receipt_id,
                Receipt.user_id == current_user.id
            )
        )
    )
    receipt = result.scalar_one_or_none()

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    # Get receipt items
    items_result = await db.execute(
        select(ReceiptItem).where(ReceiptItem.receipt_id == receipt_id)
    )
    items = items_result.scalars().all()

    return ReceiptWithItems(
        **receipt.__dict__,
        items=items
    )


@router.put("/{receipt_id}", response_model=ReceiptResponse)
async def update_receipt(
    receipt_id: uuid.UUID,
    receipt_data: ReceiptUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update receipt information.

    Typically used to correct OCR results or update metadata.
    """
    result = await db.execute(
        select(Receipt).where(
            and_(
                Receipt.id == receipt_id,
                Receipt.user_id == current_user.id
            )
        )
    )
    receipt = result.scalar_one_or_none()

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    # Update fields
    update_data = receipt_data.model_dump(exclude_unset=True, exclude={'metadata_'})
    for field, value in update_data.items():
        setattr(receipt, field, value)

    if receipt_data.metadata_ is not None:
        receipt.metadata_ = receipt_data.metadata_

    await db.commit()
    await db.refresh(receipt)

    return receipt


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a receipt and its items."""
    result = await db.execute(
        select(Receipt).where(
            and_(
                Receipt.id == receipt_id,
                Receipt.user_id == current_user.id
            )
        )
    )
    receipt = result.scalar_one_or_none()

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    await db.delete(receipt)
    await db.commit()

    return None


@router.post("/{receipt_id}/reprocess", response_model=ReceiptProcessingStatus)
async def reprocess_receipt(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocess a receipt with OCR.

    Useful if initial processing failed or needs improvement.
    """
    result = await db.execute(
        select(Receipt).where(
            and_(
                Receipt.id == receipt_id,
                Receipt.user_id == current_user.id
            )
        )
    )
    receipt = result.scalar_one_or_none()

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    # Reset processing status
    receipt.processing_status = "pending"
    receipt.processed_at = None

    await db.commit()

    # TODO: Trigger OCR processing task

    return ReceiptProcessingStatus(
        receipt_id=receipt.id,
        status="pending",
        progress=0,
        message="Receipt queued for reprocessing"
    )


@router.get("/{receipt_id}/status", response_model=ReceiptProcessingStatus)
async def get_receipt_status(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current processing status of a receipt."""
    result = await db.execute(
        select(Receipt).where(
            and_(
                Receipt.id == receipt_id,
                Receipt.user_id == current_user.id
            )
        )
    )
    receipt = result.scalar_one_or_none()

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    # Count items
    items_result = await db.execute(
        select(func.count(ReceiptItem.id)).where(ReceiptItem.receipt_id == receipt_id)
    )
    items_count = items_result.scalar() or 0

    matched_result = await db.execute(
        select(func.count(ReceiptItem.id)).where(
            and_(
                ReceiptItem.receipt_id == receipt_id,
                ReceiptItem.product_id.isnot(None)
            )
        )
    )
    matched_count = matched_result.scalar() or 0

    # Calculate progress
    progress = 100 if receipt.processing_status == "completed" else 0

    return ReceiptProcessingStatus(
        receipt_id=receipt.id,
        status=receipt.processing_status,
        progress=progress,
        message=f"Found {items_count} items, {matched_count} matched",
        items_found=items_count,
        items_matched=matched_count
    )


# Receipt Items endpoints
@router.post("/{receipt_id}/items", response_model=ReceiptItemResponse, status_code=status.HTTP_201_CREATED)
async def create_receipt_item(
    receipt_id: uuid.UUID,
    item_data: ReceiptItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add an item to a receipt (manual entry or correction)."""
    # Verify receipt exists and belongs to user
    result = await db.execute(
        select(Receipt).where(
            and_(
                Receipt.id == receipt_id,
                Receipt.user_id == current_user.id
            )
        )
    )
    receipt = result.scalar_one_or_none()

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    # Create item
    new_item = ReceiptItem(
        receipt_id=receipt_id,
        **item_data.model_dump()
    )

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    return new_item


@router.put("/items/{item_id}", response_model=ReceiptItemResponse)
async def update_receipt_item(
    item_id: uuid.UUID,
    item_data: ReceiptItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a receipt item."""
    # Get item with receipt verification
    result = await db.execute(
        select(ReceiptItem)
        .join(Receipt)
        .where(
            and_(
                ReceiptItem.id == item_id,
                Receipt.user_id == current_user.id
            )
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt item not found"
        )

    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a receipt item."""
    result = await db.execute(
        select(ReceiptItem)
        .join(Receipt)
        .where(
            and_(
                ReceiptItem.id == item_id,
                Receipt.user_id == current_user.id
            )
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt item not found"
        )

    await db.delete(item)
    await db.commit()

    return None
