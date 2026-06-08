"""Support ticket constants."""

TICKETS_COLLECTION = "support_tickets"
MESSAGES_COLLECTION = "support_messages"
OTP_COLLECTION = "support_ticket_otps"

TICKET_STATUSES = ("open", "waiting_on_customer", "resolved", "closed")
AUTHOR_TYPES = ("customer", "agent", "system")

OTP_EXPIRE_MINUTES = 15
OTP_MAX_ATTEMPTS = 5
GUEST_TOKEN_HOURS = 1

MESSAGE_MAX_LENGTH = 8000
