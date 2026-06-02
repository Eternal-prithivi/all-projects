from celery import shared_task
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@shared_task(name='check_budget_alerts')
def check_budget_alerts():
    """
    Celery task to check all active budgets and send SMS alerts if thresholds exceeded.
    Runs hourly via Celery Beat.
    
    ⚠️ OPTIMIZATION: Only runs if there are active budgets to avoid unnecessary Cost Explorer API calls.
    """
    from app.database.mongo_client import get_database
    from app.budgets.models import BudgetDB
    from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
    from app.config.demo_mode import is_demo_mode, sum_billing_total
    from app.utils.sms_notifications import send_budget_alert_sms, send_budget_exceeded_sms
    from bson import ObjectId

    if is_demo_mode():
        logger.info("⏭️  DEMO_MODE: skipping scheduled budget alerts (no billing API calls)")
        return {"budgets_checked": 0, "alerts_sent": 0, "skipped": True, "reason": "demo_mode"}

    DB = get_database()
    budgets_collection = DB["budgets"]
    
    # OPTIMIZATION: Check if there are any active budgets first
    active_budget_count = budgets_collection.count_documents({"is_active": True})
    if active_budget_count == 0:
        logger.info("⏭️  No active budgets found. Skipping budget check to save Cost Explorer API calls.")
        return {"budgets_checked": 0, "alerts_sent": 0, "skipped": True, "reason": "No active budgets"}
    
    logger.info(f"Starting automatic budget check for {active_budget_count} active budget(s)...")
    
    try:
        # Find all active budgets
        cursor = budgets_collection.find({"is_active": True})
        budgets_checked = 0
        alerts_sent = 0
        
        for doc in cursor:
            budgets_checked += 1
            doc["id"] = str(doc["_id"])
            doc.pop("_id", None)
            budget = BudgetDB(**doc)
            
            # Calculate period start based on budget period
            if budget.period == "daily":
                from datetime import datetime, timedelta
                period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            elif budget.period == "weekly":
                from datetime import datetime, timedelta
                today = datetime.utcnow()
                period_start = today - timedelta(days=today.weekday())
                period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # monthly
                from datetime import datetime
                period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            start_date = period_start.strftime("%Y-%m-%d")
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Fetch current spend
            current_spend = 0.0
            try:
                if budget.provider == "all":
                    aws_data = get_aws_cost_and_usage(
                        budget.user_id, start_date, end_date, "DAILY"
                    )
                    gcp_data = get_gcp_billing_data(budget.user_id, start_date, end_date)
                    azure_data = get_azure_billing_data(budget.user_id, start_date, end_date)
                    
                    current_spend += sum_billing_total(aws_data)
                    current_spend += sum_billing_total(gcp_data)
                    current_spend += sum_billing_total(azure_data)
                elif budget.provider == "aws":
                    aws_data = get_aws_cost_and_usage(
                        budget.user_id, start_date, end_date, "DAILY"
                    )
                    current_spend = sum_billing_total(aws_data)
                elif budget.provider == "gcp":
                    gcp_data = get_gcp_billing_data(budget.user_id, start_date, end_date)
                    current_spend = sum_billing_total(gcp_data)
                elif budget.provider == "azure":
                    azure_data = get_azure_billing_data(budget.user_id, start_date, end_date)
                    current_spend = sum_billing_total(azure_data)
            except Exception as cost_error:
                logger.warning(f"Error fetching cost data for budget {budget.id}: {str(cost_error)}")
                continue
            
            # Update current spend in database
            budgets_collection.update_one(
                {"_id": ObjectId(budget.id)},
                {"$set": {"current_spend": current_spend, "updated_at": datetime.utcnow()}}
            )
            
            # Calculate status
            utilization = (current_spend / budget.amount * 100) if budget.amount > 0 else 0
            is_exceeded = current_spend >= budget.amount
            is_near_limit = utilization >= budget.alert_threshold
            
            logger.info(f"Budget '{budget.name}': spend=${current_spend:.2f}, limit=${budget.amount:.2f}, utilization={utilization:.1f}%")
            
            # Send SMS if phone number provided and threshold crossed
            if budget.phone_number and (is_near_limit or is_exceeded):
                # Check if we haven't alerted recently (prevent spam)
                should_alert = True
                if budget.last_alerted:
                    time_since_last_alert = (datetime.utcnow() - budget.last_alerted).total_seconds() / 3600
                    should_alert = time_since_last_alert >= 1.0
                
                if should_alert:
                    try:
                        if is_exceeded:
                            send_budget_exceeded_sms(budget.phone_number, budget.name, current_spend, budget.amount)
                            logger.info(f"✅ Sent EXCEEDED SMS for budget '{budget.name}' to {budget.phone_number}")
                        else:
                            send_budget_alert_sms(budget.phone_number, budget.name, utilization, budget.amount, current_spend)
                            logger.info(f"✅ Sent ALERT SMS for budget '{budget.name}' to {budget.phone_number}")
                        
                        # Update last alerted time
                        budgets_collection.update_one(
                            {"_id": ObjectId(budget.id)},
                            {"$set": {"last_alerted": datetime.utcnow()}}
                        )
                        alerts_sent += 1
                    except Exception as sms_error:
                        logger.error(f"Failed to send SMS for budget '{budget.name}': {str(sms_error)}")
        
        logger.info(f"Budget check complete: {budgets_checked} budgets checked, {alerts_sent} alerts sent")
        return {"budgets_checked": budgets_checked, "alerts_sent": alerts_sent}
        
    except Exception as e:
        logger.error(f"Error in budget check task: {str(e)}")
        raise
