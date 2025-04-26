"""
Data model for user information
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class UserSettings(BaseModel):
    """Model for user-specific settings"""
    default_currency: str = "USD"
    default_report_type: str = "monthly"
    default_email: Optional[str] = None
    email_notifications: bool = False
    preferred_language: str = "en"
    default_categories: List[str] = ["Groceries", "Dining", "Entertainment", "Transportation", "Other"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            "default_currency": self.default_currency,
            "default_report_type": self.default_report_type,
            "default_email": self.default_email,
            "email_notifications": self.email_notifications,
            "preferred_language": self.preferred_language,
            "default_categories": self.default_categories
        }


class Budget(BaseModel):
    """Model for budget information"""
    category: str
    amount: float
    period: str = "monthly"  # "daily", "weekly", "monthly", "annual"
    start_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert budget to dictionary"""
        return {
            "category": self.category,
            "amount": self.amount,
            "period": self.period,
            "start_date": self.start_date
        }


class User(BaseModel):
    """Model for user data"""
    user_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    settings: UserSettings = Field(default_factory=UserSettings)
    budgets: List[Budget] = []
    join_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    last_active: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "settings": self.settings.to_dict(),
            "budgets": [budget.to_dict() for budget in self.budgets],
            "join_date": self.join_date,
            "last_active": self.last_active
        }
    
    def update_last_active(self) -> None:
        """Update the last active timestamp"""
        self.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def add_budget(self, category: str, amount: float, period: str = "monthly") -> None:
        """
        Add a new budget for a category
        
        Args:
            category: Expense category
            amount: Budget amount
            period: Budget period (daily, weekly, monthly, annual)
        """
        # Remove any existing budget for this category and period
        self.budgets = [b for b in self.budgets if not (b.category == category and b.period == period)]
        
        # Add the new budget
        self.budgets.append(Budget(
            category=category,
            amount=amount,
            period=period,
            start_date=datetime.now().strftime("%Y-%m-%d")
        ))
    
    def get_budget(self, category: str, period: str = "monthly") -> Optional[Budget]:
        """
        Get budget for a specific category and period
        
        Args:
            category: Expense category
            period: Budget period
            
        Returns:
            Budget if found, None otherwise
        """
        for budget in self.budgets:
            if budget.category == category and budget.period == period:
                return budget
        return None
    
    @classmethod
    def from_telegram_user(cls, telegram_user):
        """
        Create a User instance from a Telegram user object
        
        Args:
            telegram_user: Telegram User object
            
        Returns:
            User instance
        """
        return cls(
            user_id=telegram_user.id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username
        )