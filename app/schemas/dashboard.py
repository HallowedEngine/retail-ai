"""
Pydantic schemas for Dashboard endpoints.
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Dashboard summary with key metrics."""
    # Product metrics
    total_products: int
    active_products: int
    low_stock_products: int
    out_of_stock_products: int

    # Stock metrics
    total_stock_value: Optional[Decimal] = None
    total_stock_items: int

    # Alert metrics
    total_alerts: int
    unread_alerts: int
    critical_alerts: int

    # Receipt metrics
    total_receipts: int
    pending_receipts: int
    receipts_today: int

    # Transaction metrics
    transactions_today: int
    transactions_this_week: int

    # Time info
    last_updated: datetime


class DashboardChartData(BaseModel):
    """Chart data for dashboard visualizations."""
    labels: list[str]
    datasets: list[dict]


class StockTrendData(BaseModel):
    """Stock trend data over time."""
    date: str
    total_stock: int
    stock_in: int
    stock_out: int
    stock_value: Optional[Decimal] = None


class CategoryDistribution(BaseModel):
    """Product distribution by category."""
    category: str
    count: int
    percentage: float
    stock_value: Optional[Decimal] = None


class RecentActivity(BaseModel):
    """Recent activity item."""
    type: str  # 'receipt', 'stock', 'alert', 'product'
    title: str
    description: Optional[str] = None
    timestamp: datetime
    severity: Optional[str] = None
    link: Optional[str] = None


class DashboardCharts(BaseModel):
    """All dashboard chart data."""
    stock_trend: list[StockTrendData]
    category_distribution: list[CategoryDistribution]
    weekly_receipts: DashboardChartData
    alert_distribution: dict[str, int]


class DashboardRecent(BaseModel):
    """Recent activities for dashboard."""
    activities: list[RecentActivity]
    total: int


class HealthCheck(BaseModel):
    """Health check response."""
    status: str  # 'healthy', 'degraded', 'unhealthy'
    version: str
    database: bool
    redis: Optional[bool] = None
    timestamp: datetime
