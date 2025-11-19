"""
Pydantic schemas for request/response validation.
"""
from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserChangePassword, UserResponse,
    TokenData, Token, TokenRefresh, LoginRequest, LoginResponse
)
from app.schemas.product import (
    ProductBase, ProductCreate, ProductUpdate, ProductResponse,
    ProductWithStock, ProductListResponse, ProductBulkCreate, ProductBulkCreateResponse
)
from app.schemas.receipt import (
    ReceiptItemBase, ReceiptItemCreate, ReceiptItemUpdate, ReceiptItemResponse,
    ReceiptBase, ReceiptCreate, ReceiptUpdate, ReceiptResponse,
    ReceiptWithItems, ReceiptListResponse, ReceiptUploadResponse, ReceiptProcessingStatus
)
from app.schemas.stock import (
    TransactionType, ReferenceType, StockTransactionBase, StockTransactionCreate,
    StockAdjustment, StockTransactionResponse, StockTransactionWithProduct,
    StockTransactionListResponse, StockSummary, StockStats
)
from app.schemas.alert import (
    AlertType, AlertSeverity, AlertBase, AlertCreate, AlertUpdate,
    AlertResponse, AlertWithProduct, AlertListResponse, AlertStats
)
from app.schemas.dashboard import (
    DashboardSummary, DashboardChartData, StockTrendData, CategoryDistribution,
    RecentActivity, DashboardCharts, DashboardRecent, HealthCheck
)

__all__ = [
    # User schemas
    "UserBase", "UserCreate", "UserUpdate", "UserChangePassword", "UserResponse",
    "TokenData", "Token", "TokenRefresh", "LoginRequest", "LoginResponse",

    # Product schemas
    "ProductBase", "ProductCreate", "ProductUpdate", "ProductResponse",
    "ProductWithStock", "ProductListResponse", "ProductBulkCreate", "ProductBulkCreateResponse",

    # Receipt schemas
    "ReceiptItemBase", "ReceiptItemCreate", "ReceiptItemUpdate", "ReceiptItemResponse",
    "ReceiptBase", "ReceiptCreate", "ReceiptUpdate", "ReceiptResponse",
    "ReceiptWithItems", "ReceiptListResponse", "ReceiptUploadResponse", "ReceiptProcessingStatus",

    # Stock schemas
    "TransactionType", "ReferenceType", "StockTransactionBase", "StockTransactionCreate",
    "StockAdjustment", "StockTransactionResponse", "StockTransactionWithProduct",
    "StockTransactionListResponse", "StockSummary", "StockStats",

    # Alert schemas
    "AlertType", "AlertSeverity", "AlertBase", "AlertCreate", "AlertUpdate",
    "AlertResponse", "AlertWithProduct", "AlertListResponse", "AlertStats",

    # Dashboard schemas
    "DashboardSummary", "DashboardChartData", "StockTrendData", "CategoryDistribution",
    "RecentActivity", "DashboardCharts", "DashboardRecent", "HealthCheck",
]
