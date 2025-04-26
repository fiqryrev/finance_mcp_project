"""
Data model for receipts and receipt items
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ReceiptItem(BaseModel):
    """Model for an individual item on a receipt"""
    name: str
    price: str
    quantity: Optional[str] = "1"
    unit_price: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "unit_price": self.unit_price
        }


class Receipt(BaseModel):
    """Model for a full receipt"""
    date: Optional[str] = None
    merchant: Optional[str] = None
    total: Optional[str] = None
    subtotal: Optional[str] = None
    tax: Optional[str] = None
    payment_method: Optional[str] = None
    category: Optional[str] = "Uncategorized"
    items: List[ReceiptItem] = []
    upload_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "date": self.date,
            "merchant": self.merchant,
            "total": self.total,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "payment_method": self.payment_method,
            "category": self.category,
            "items": [item.to_dict() for item in self.items],
            "upload_date": self.upload_date,
            "notes": self.notes
        }
    
    @classmethod
    def from_ocr_result(cls, ocr_result: Dict[str, Any]) -> 'Receipt':
        """
        Create a Receipt instance from OCR result dictionary
        
        Args:
            ocr_result: Dictionary from OCR processing
            
        Returns:
            Receipt instance
        """
        # Convert items dictionaries to ReceiptItem instances
        items = []
        for item_dict in ocr_result.get('items', []):
            items.append(ReceiptItem(
                name=item_dict.get('name', 'Unknown Item'),
                price=item_dict.get('price', '0.00'),
                quantity=item_dict.get('quantity', '1'),
                unit_price=item_dict.get('unit_price')
            ))
        
        # Create and return Receipt instance
        return cls(
            date=ocr_result.get('date'),
            merchant=ocr_result.get('merchant'),
            total=ocr_result.get('total'),
            subtotal=ocr_result.get('subtotal'),
            tax=ocr_result.get('tax'),
            payment_method=ocr_result.get('payment_method'),
            category=ocr_result.get('category', 'Uncategorized'),
            items=items
        )