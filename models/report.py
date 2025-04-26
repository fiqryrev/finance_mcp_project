"""
Data model for financial reports
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CategoryExpense(BaseModel):
    """Model for expenses within a category"""
    category: str
    amount: float
    transaction_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert category expense to dictionary"""
        return {
            "category": self.category,
            "amount": self.amount,
            "transaction_count": self.transaction_count
        }


class MerchantExpense(BaseModel):
    """Model for expenses by merchant"""
    merchant: str
    amount: float
    transaction_count: int = 0
    categories: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert merchant expense to dictionary"""
        return {
            "merchant": self.merchant,
            "amount": self.amount,
            "transaction_count": self.transaction_count,
            "categories": self.categories
        }


class Insight(BaseModel):
    """Model for financial insights"""
    insight_type: str  # "spending_pattern", "budget_alert", "recommendation", etc.
    description: str
    importance: int = 1  # 1-5 scale, 5 being highest importance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert insight to dictionary"""
        return {
            "insight_type": self.insight_type,
            "description": self.description,
            "importance": self.importance
        }


class Report(BaseModel):
    """Model for a financial report"""
    report_id: str = Field(default_factory=lambda: f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    report_type: str  # "daily", "weekly", "monthly", "custom"
    start_date: str
    end_date: str
    total_expenses: float = 0.0
    total_transactions: int = 0
    category_expenses: List[CategoryExpense] = []
    merchant_expenses: List[MerchantExpense] = []
    insights: List[Insight] = []
    generation_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    spreadsheet_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_expenses": self.total_expenses,
            "total_transactions": self.total_transactions,
            "category_expenses": [cat.to_dict() for cat in self.category_expenses],
            "merchant_expenses": [merch.to_dict() for merch in self.merchant_expenses],
            "insights": [insight.to_dict() for insight in self.insights],
            "generation_date": self.generation_date,
            "spreadsheet_url": self.spreadsheet_url
        }
    
    def add_category_expense(self, category: str, amount: float, transaction_count: int = 1) -> None:
        """
        Add or update category expense
        
        Args:
            category: Expense category
            amount: Expense amount
            transaction_count: Number of transactions
        """
        # Check if category already exists
        for cat_expense in self.category_expenses:
            if cat_expense.category == category:
                # Update existing category
                cat_expense.amount += amount
                cat_expense.transaction_count += transaction_count
                return
        
        # Add new category
        self.category_expenses.append(CategoryExpense(
            category=category,
            amount=amount,
            transaction_count=transaction_count
        ))
        
        # Update total expenses
        self.total_expenses += amount
        self.total_transactions += transaction_count
    
    def add_merchant_expense(self, merchant: str, amount: float, 
                           transaction_count: int = 1, categories: List[str] = None) -> None:
        """
        Add or update merchant expense
        
        Args:
            merchant: Merchant name
            amount: Expense amount
            transaction_count: Number of transactions
            categories: List of categories for this merchant
        """
        # Initialize categories if None
        if categories is None:
            categories = []
        
        # Check if merchant already exists
        for merch_expense in self.merchant_expenses:
            if merch_expense.merchant == merchant:
                # Update existing merchant
                merch_expense.amount += amount
                merch_expense.transaction_count += transaction_count
                # Add any new categories
                for category in categories:
                    if category not in merch_expense.categories:
                        merch_expense.categories.append(category)
                return
        
        # Add new merchant
        self.merchant_expenses.append(MerchantExpense(
            merchant=merchant,
            amount=amount,
            transaction_count=transaction_count,
            categories=categories
        ))
    
    def add_insight(self, insight_type: str, description: str, importance: int = 1) -> None:
        """
        Add an insight to the report
        
        Args:
            insight_type: Type of insight
            description: Insight description
            importance: Importance level (1-5)
        """
        self.insights.append(Insight(
            insight_type=insight_type,
            description=description,
            importance=importance
        ))
    
    def get_top_categories(self, limit: int = 5) -> List[CategoryExpense]:
        """
        Get top expense categories
        
        Args:
            limit: Number of categories to return
            
        Returns:
            List of top category expenses
        """
        return sorted(self.category_expenses, key=lambda x: x.amount, reverse=True)[:limit]
    
    def get_top_merchants(self, limit: int = 5) -> List[MerchantExpense]:
        """
        Get top merchants by expense
        
        Args:
            limit: Number of merchants to return
            
        Returns:
            List of top merchant expenses
        """
        return sorted(self.merchant_expenses, key=lambda x: x.amount, reverse=True)[:limit]
    
    def get_period_description(self) -> str:
        """
        Get a human-readable description of the report period
        
        Returns:
            Period description string
        """
        try:
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
            
            # Format dates
            start_formatted = start.strftime("%B %d, %Y")
            end_formatted = end.strftime("%B %d, %Y")
            
            return f"{start_formatted} to {end_formatted}"
        except:
            return f"{self.start_date} to {self.end_date}"