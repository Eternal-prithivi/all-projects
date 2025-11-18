from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from datetime import datetime, timedelta
from bson import ObjectId
import logging

from app.auth.auth_utils import get_current_user
from app.database.mongo_client import get_database
from .models import BudgetCreate, BudgetUpdate, BudgetDB, BudgetStatus

router = APIRouter()
logger = logging.getLogger(__name__)

DB = get_database()
budgets_collection = DB["budgets"]

def calculate_period_start(period: str) -> datetime:
    """Calculate the start date for the budget period"""
    now = datetime.utcnow()
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        return now - timedelta(days=now.weekday())
    elif period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "yearly":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now

@router.post("/", response_model=BudgetDB, status_code=status.HTTP_201_CREATED)
async def create_budget(budget: BudgetCreate):
    """Create a new budget alert"""
    try:
        budget_doc = {
            "user_id": "default_user",  # Default user for non-authenticated access
            "name": budget.name,
            "amount": budget.amount,
            "provider": budget.provider,
            "period": budget.period,
            "alert_threshold": budget.alert_threshold,
            "email_notifications": budget.email_notifications,
            "phone_number": budget.phone_number,
            "is_active": True,
            "current_spend": 0.0,
            "last_alerted": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = budgets_collection.insert_one(budget_doc)
        budget_doc["id"] = str(result.inserted_id)
        budget_doc.pop("_id", None)
        
        return BudgetDB(**budget_doc)
    except Exception as e:
        logger.error(f"Error creating budget: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create budget: {str(e)}")

@router.get("/", response_model=List[BudgetDB])
async def get_budgets():
    """Get all budgets for the current user"""
    try:
        budgets = []
        cursor = budgets_collection.find({"user_id": "default_user"})  # Default user for non-authenticated access
        
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            doc.pop("_id", None)
            budgets.append(BudgetDB(**doc))
        
        return budgets
    except Exception as e:
        logger.error(f"Error fetching budgets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch budgets: {str(e)}")

@router.get("/status", response_model=List[BudgetStatus])
async def get_budget_status():
    """Get status of all budgets with current spending"""
    try:
        from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
        
        budgets = []
        cursor = budgets_collection.find({"user_id": "default_user", "is_active": True})  # Default user
        
        statuses = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            doc.pop("_id", None)
            budget = BudgetDB(**doc)
            
            # Calculate current spend for the period
            period_start = calculate_period_start(budget.period)
            start_date = period_start.strftime("%Y-%m-%d")
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            current_spend = 0.0
            try:
                if budget.provider == "all":
                    # Sum all providers
                    aws_data = get_aws_cost_and_usage(start_date, end_date, "DAILY")
                    gcp_data = get_gcp_billing_data(start_date, end_date)
                    azure_data = get_azure_billing_data(start_date, end_date)
                    
                    current_spend += sum(float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0)) 
                                       for item in aws_data.get("data", {}).get("ResultsByTime", []))
                    current_spend += sum(float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0)) 
                                       for item in gcp_data.get("data", {}).get("ResultsByTime", []))
                    current_spend += sum(float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0)) 
                                       for item in azure_data.get("data", {}).get("ResultsByTime", []))
                elif budget.provider == "aws":
                    aws_data = get_aws_cost_and_usage(start_date, end_date, "DAILY")
                    current_spend = sum(float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0)) 
                                      for item in aws_data.get("data", {}).get("ResultsByTime", []))
                elif budget.provider == "gcp":
                    gcp_data = get_gcp_billing_data(start_date, end_date)
                    current_spend = sum(float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0)) 
                                      for item in gcp_data.get("data", {}).get("ResultsByTime", []))
                elif budget.provider == "azure":
                    azure_data = get_azure_billing_data(start_date, end_date)
                    current_spend = sum(float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0)) 
                                      for item in azure_data.get("data", {}).get("ResultsByTime", []))
            except Exception as cost_error:
                logger.warning(f"Error fetching cost data for budget {budget.id}: {str(cost_error)}")
            
            # Update current spend in database
            budgets_collection.update_one(
                {"_id": ObjectId(budget.id)},
                {"$set": {"current_spend": current_spend, "updated_at": datetime.utcnow()}}
            )
            budget.current_spend = current_spend
            
            # Calculate status
            utilization = (current_spend / budget.amount * 100) if budget.amount > 0 else 0
            is_exceeded = current_spend >= budget.amount
            is_near_limit = utilization >= budget.alert_threshold
            remaining = max(0, budget.amount - current_spend)
            
            # Debug logging
            logger.info(f"Budget '{budget.name}': spend=${current_spend:.4f}, limit=${budget.amount:.4f}, utilization={utilization:.2f}%, phone={budget.phone_number}, near_limit={is_near_limit}, exceeded={is_exceeded}")
            
            # Send SMS notifications if phone number provided and threshold crossed
            if budget.phone_number and (is_near_limit or is_exceeded):
                logger.info(f"SMS conditions met for budget '{budget.name}'")
                # Check if we haven't alerted recently (prevent spam)
                should_alert = True
                if budget.last_alerted:
                    # Only alert once per hour
                    time_since_last_alert = (datetime.utcnow() - budget.last_alerted).total_seconds() / 3600
                    should_alert = time_since_last_alert >= 1.0
                    logger.info(f"Last alerted {time_since_last_alert:.2f} hours ago, should_alert={should_alert}")
                
                if should_alert:
                    logger.info(f"Attempting to send SMS to {budget.phone_number}")
                    from app.utils.sms_notifications import send_budget_alert_sms, send_budget_exceeded_sms
                    
                    if is_exceeded:
                        result = send_budget_exceeded_sms(budget.phone_number, budget.name, current_spend, budget.amount)
                        logger.info(f"SMS exceeded result: {result}")
                    else:
                        result = send_budget_alert_sms(budget.phone_number, budget.name, current_spend, budget.amount, utilization)
                        logger.info(f"SMS alert result: {result}")
                    
                    # Update last_alerted timestamp
                    budgets_collection.update_one(
                        {"_id": ObjectId(budget.id)},
                        {"$set": {"last_alerted": datetime.utcnow()}}
                    )
            
            statuses.append(BudgetStatus(
                budget=budget,
                utilization_percentage=round(utilization, 2),
                is_exceeded=is_exceeded,
                is_near_limit=is_near_limit,
                remaining_amount=round(remaining, 2)
            ))
        
        return statuses
    except Exception as e:
        logger.error(f"Error calculating budget status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate budget status: {str(e)}")

@router.get("/{budget_id}", response_model=BudgetDB)
async def get_budget(budget_id: str):
    """Get a specific budget by ID"""
    try:
        doc = budgets_collection.find_one({"_id": ObjectId(budget_id), "user_id": "default_user"})
        if not doc:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        return BudgetDB(**doc)
    except Exception as e:
        logger.error(f"Error fetching budget: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch budget: {str(e)}")

@router.put("/{budget_id}", response_model=BudgetDB)
async def update_budget(budget_id: str, budget: BudgetUpdate):
    """Update a budget"""
    try:
        update_data = {k: v for k, v in budget.dict(exclude_unset=True).items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = budgets_collection.update_one(
            {"_id": ObjectId(budget_id), "user_id": "default_user"},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        doc = budgets_collection.find_one({"_id": ObjectId(budget_id)})
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        return BudgetDB(**doc)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating budget: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update budget: {str(e)}")

@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(budget_id: str):
    """Delete a budget"""
    try:
        result = budgets_collection.delete_one({"_id": ObjectId(budget_id), "user_id": "default_user"})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Budget not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting budget: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete budget: {str(e)}")

@router.post("/test-sms")
async def test_sms(phone_number: str, budget_name: str = "Test Budget"):
    """Test SMS notification - sends immediately"""
    try:
        from app.utils.sms_notifications import send_budget_alert_sms
        
        logger.info(f"Testing SMS to {phone_number}")
        result = send_budget_alert_sms(phone_number, budget_name, 85.0, 100.0, 85.0)
        
        if result:
            return {"success": True, "message": f"SMS sent successfully to {phone_number}"}
        else:
            return {"success": False, "message": "SMS failed to send - check logs for details"}
    except Exception as e:
        logger.error(f"Error testing SMS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send test SMS: {str(e)}")

