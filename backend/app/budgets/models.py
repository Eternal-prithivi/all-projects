from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class BudgetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    provider: Literal["aws", "gcp", "azure", "all"]
    period: Literal["daily", "weekly", "monthly", "yearly"]
    alert_threshold: float = Field(default=80, ge=0, le=100)  # Alert at 80% by default
    email_notifications: bool = True
    phone_number: Optional[str] = None  # For SMS notifications (format: +1234567890)

class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    amount: Optional[float] = Field(None, gt=0)
    alert_threshold: Optional[float] = Field(None, ge=0, le=100)
    email_notifications: Optional[bool] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None

class BudgetDB(BaseModel):
    id: str
    user_id: str
    name: str
    amount: float
    provider: str
    period: str
    alert_threshold: float
    email_notifications: bool
    phone_number: Optional[str] = None
    is_active: bool
    current_spend: float = 0.0
    last_alerted: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BudgetStatus(BaseModel):
    budget: BudgetDB
    utilization_percentage: float
    is_exceeded: bool
    is_near_limit: bool
    remaining_amount: float
