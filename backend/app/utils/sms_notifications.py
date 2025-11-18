import os
import logging
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

def send_sms(to_phone: str, message: str) -> bool:
    """
    Send SMS notification using Twilio
    
    Args:
        to_phone: Recipient phone number (format: +1234567890)
        message: SMS message content (max 160 characters recommended)
        
    Returns:
        bool: True if SMS sent successfully, False otherwise
    """
    try:
        # Check if Twilio is configured
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            logger.warning("Twilio not configured. SMS not sent. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env")
            return False
        
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send SMS
        message_obj = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        
        logger.info(f"SMS sent successfully to {to_phone}. SID: {message_obj.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_phone}: {str(e)}")
        return False


def send_budget_alert_sms(phone_number: str, budget_name: str, current_spend: float, budget_amount: float, utilization: float):
    """
    Send budget alert SMS notification
    
    Args:
        phone_number: Recipient phone number
        budget_name: Name of the budget
        current_spend: Current spending amount
        budget_amount: Total budget amount
        utilization: Utilization percentage
    """
    threshold_amount = budget_amount * (utilization / 100)
    message = f"[Zenith Cloud Platform] Budget Alert: '{budget_name}' has reached {utilization:.1f}% utilization (${threshold_amount:.2f} threshold). Current spend: ${current_spend:.2f} of ${budget_amount:.2f} allocated. Review your cloud resources to optimize costs."
    return send_sms(phone_number, message)


def send_budget_exceeded_sms(phone_number: str, budget_name: str, current_spend: float, budget_amount: float):
    """
    Send budget exceeded SMS notification
    
    Args:
        phone_number: Recipient phone number
        budget_name: Name of the budget
        current_spend: Current spending amount
        budget_amount: Total budget amount
    """
    overage = current_spend - budget_amount
    message = f"[Zenith Cloud Platform] URGENT: Budget '{budget_name}' exceeded! Current spend: ${current_spend:.2f} | Budget limit: ${budget_amount:.2f} | Overage: ${overage:.2f}. Immediate action recommended."
    return send_sms(phone_number, message)
