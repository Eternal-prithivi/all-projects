"""
Standardized API response utilities.
"""
from typing import Any, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse

class StandardResponse:
    """Standardized API response format."""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200
    ) -> dict:
        """
        Create a standardized success response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            
        Returns:
            Standardized response dictionary
        """
        response = {
            "success": True,
            "message": message,
        }
        if data is not None:
            response["data"] = data
        return response
    
    @staticmethod
    def error(
        message: str,
        status_code: int = 400,
        errors: Optional[dict] = None,
        error_code: Optional[str] = None
    ) -> HTTPException:
        """
        Create a standardized error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            errors: Additional error details
            error_code: Application-specific error code
            
        Returns:
            HTTPException with standardized format
        """
        detail = {
            "success": False,
            "message": message,
        }
        if error_code:
            detail["error_code"] = error_code
        if errors:
            detail["errors"] = errors
            
        return HTTPException(status_code=status_code, detail=detail)

# Common error responses
class ErrorResponses:
    """Pre-defined common error responses."""
    
    @staticmethod
    def unauthorized(message: str = "Authentication required"):
        return StandardResponse.error(message, 401, error_code="UNAUTHORIZED")
    
    @staticmethod
    def forbidden(message: str = "Access denied"):
        return StandardResponse.error(message, 403, error_code="FORBIDDEN")
    
    @staticmethod
    def not_found(resource: str = "Resource"):
        return StandardResponse.error(f"{resource} not found", 404, error_code="NOT_FOUND")
    
    @staticmethod
    def bad_request(message: str = "Invalid request", errors: dict = None):
        return StandardResponse.error(message, 400, errors=errors, error_code="BAD_REQUEST")
    
    @staticmethod
    def conflict(message: str = "Resource already exists"):
        return StandardResponse.error(message, 409, error_code="CONFLICT")
    
    @staticmethod
    def internal_error(message: str = "Internal server error"):
        return StandardResponse.error(message, 500, error_code="INTERNAL_ERROR")
    
    @staticmethod
    def rate_limit_exceeded(message: str = "Rate limit exceeded. Please try again later."):
        return StandardResponse.error(message, 429, error_code="RATE_LIMIT_EXCEEDED")
    
    @staticmethod
    def validation_error(errors: dict):
        return StandardResponse.error(
            "Validation failed",
            422,
            errors=errors,
            error_code="VALIDATION_ERROR"
        )
