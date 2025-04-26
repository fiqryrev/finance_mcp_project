"""
Service for processing images and documents using LLM-based OCR
"""
import os
import asyncio
from typing import Dict, Any, List, Optional
import base64
from PIL import Image
import io
import fitz  # PyMuPDF for PDF processing
import tempfile

from services.llm_service import LLMService
from config.config import OCR_CONFIDENCE_THRESHOLD

class OCRService:
    """Service for processing receipts and invoices using LLM OCR capabilities"""
    
    def __init__(self):
        """Initialize the OCR service with LLM client"""
        self.llm_service = LLMService()
        self.confidence_threshold = OCR_CONFIDENCE_THRESHOLD
    
    async def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process an image of a receipt or invoice using LLM vision capabilities
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with extracted information
        """
        # Read the image using PIL to prepare it for LLM processing
        try:
            with Image.open(image_path) as img:
                # Optionally resize or optimize image for better OCR results
                if max(img.size) > 1600:
                    ratio = 1600 / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # Process image with LLM
                prompt = self._create_receipt_ocr_prompt()
                result = await self.llm_service.process_image(image_path, prompt)
                
                # Parse LLM response to structured data
                structured_data = self._parse_receipt_response(result)
                
                return structured_data
                
        except Exception as e:
            raise Exception(f"Error processing image: {e}")
    
    async def process_document(self, document_path: str, file_ext: str) -> Dict[str, Any]:
        """
        Process a document file (PDF, etc.) using LLM
        
        Args:
            document_path: Path to the document file
            file_ext: File extension to determine processing method
            
        Returns:
            Dictionary with extracted information
        """
        try:
            # For PDF documents
            if file_ext.lower() == '.pdf':
                return await self._process_pdf(document_path)
            # For other document types, try to process as image
            else:
                return await self.process_image(document_path)
        except Exception as e:
            raise Exception(f"Error processing document: {e}")
    
    async def _process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a PDF document by converting pages to images and using OCR
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted information
        """
        try:
            # Open the PDF
            pdf_document = fitz.open(pdf_path)
            
            # For multi-page PDFs, process the first few pages (usually receipts are 1-2 pages)
            max_pages = min(2, len(pdf_document))
            
            all_results = []
            for page_num in range(max_pages):
                # Get the page
                page = pdf_document[page_num]
                
                # Render page to image with higher resolution for better OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                # Save the image to a temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_path = temp_file.name
                    pix.save(temp_path)
                
                # Process the page image
                page_result = await self.process_image(temp_path)
                all_results.append(page_result)
                
                # Remove temporary file
                os.unlink(temp_path)
            
            # Combine results if multiple pages were processed
            if len(all_results) > 1:
                combined_result = self._combine_results(all_results)
                return combined_result
            elif len(all_results) == 1:
                return all_results[0]
            else:
                return {"error": "No valid data extracted from PDF"}
            
        except Exception as e:
            raise Exception(f"Error processing PDF: {e}")
    
    def _combine_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results from multiple pages into one coherent result
        
        Args:
            results: List of results from individual pages
            
        Returns:
            Combined result dictionary
        """
        # Start with the first result as base
        combined = results[0].copy()
        
        # Combine items lists if present
        all_items = []
        for result in results:
            if 'items' in result and result['items']:
                all_items.extend(result['items'])
        
        if all_items:
            combined['items'] = all_items
        
        # For other fields, use the most confident value or the first non-empty one
        for field in ['date', 'merchant', 'total', 'subtotal', 'tax']:
            values = [r.get(field) for r in results if r.get(field)]
            if values:
                # For now, just use the first valid value
                combined[field] = values[0]
        
        return combined
    
    def _create_receipt_ocr_prompt(self) -> str:
        """
        Create a prompt for the LLM to extract information from a receipt
        
        Returns:
            Prompt string
        """
        return """
        Extract detailed information from this receipt or invoice image. Please provide the following information in a structured format:

        1. Date of purchase
        2. Merchant/vendor name
        3. Total amount
        4. Subtotal (before tax)
        5. Tax amount
        6. Payment method (if available)
        7. List of purchased items with:
           - Item name
           - Quantity
           - Price per item
           - Total price

        Return the information in the following JSON format exactly:
        {
          "date": "YYYY-MM-DD",
          "merchant": "Merchant Name",
          "total": "XX.XX",
          "subtotal": "XX.XX",
          "tax": "XX.XX",
          "payment_method": "Credit Card/Cash/etc.",
          "items": [
            {
              "name": "Item Description",
              "quantity": "X",
              "unit_price": "XX.XX",
              "price": "XX.XX"
            },
            ...
          ]
        }

        If any field is not found in the receipt, use null for that field. For the items list, include as many items as you can clearly identify.
        """
    
    def _parse_receipt_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured dictionary
        
        Args:
            response: LLM response string
            
        Returns:
            Structured dictionary with receipt data
        """
        try:
            import json
            import re
            
            # Try to extract JSON from the response
            json_match = re.search(r'{.*}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data
            else:
                # If no JSON found, try to parse in a more forgiving way
                return self._fallback_parse_receipt(response)
                
        except Exception as e:
            raise Exception(f"Error parsing OCR response: {e}")
    
    def _fallback_parse_receipt(self, response: str) -> Dict[str, Any]:
        """
        Fallback method to extract information from non-JSON LLM responses
        
        Args:
            response: LLM response text
            
        Returns:
            Structured dictionary with receipt data
        """
        import re
        
        # Initialize empty result
        result = {
            "date": None,
            "merchant": None,
            "total": None,
            "subtotal": None,
            "tax": None,
            "payment_method": None,
            "items": []
        }
        
        # Extract date
        date_match = re.search(r'Date:?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', response)
        if date_match:
            result["date"] = date_match.group(1)
        
        # Extract merchant
        merchant_match = re.search(r'Merchant:?\s*([^\n]+)', response)
        if merchant_match:
            result["merchant"] = merchant_match.group(1).strip()
        
        # Extract total amount
        total_match = re.search(r'Total:?\s*\$?([0-9]+\.[0-9]{2})', response)
        if total_match:
            result["total"] = total_match.group(1)
        
        # Extract subtotal
        subtotal_match = re.search(r'Subtotal:?\s*\$?([0-9]+\.[0-9]{2})', response)
        if subtotal_match:
            result["subtotal"] = subtotal_match.group(1)
        
        # Extract tax
        tax_match = re.search(r'Tax:?\s*\$?([0-9]+\.[0-9]{2})', response)
        if tax_match:
            result["tax"] = tax_match.group(1)
        
        # Extract payment method
        payment_match = re.search(r'Payment Method:?\s*([^\n]+)', response)
        if payment_match:
            result["payment_method"] = payment_match.group(1).strip()
        
        # Try to extract items - this is more complex and might need refinement
        items_section = re.search(r'Items:(.*?)(?=\n\n|\Z)', response, re.DOTALL)
        if items_section:
            items_text = items_section.group(1)
            # Look for patterns like "Item name: $XX.XX" or "X Item name - $XX.XX"
            item_matches = re.finditer(r'[-•*]?\s*([^:$\n]+)[:-]\s*\$?([0-9]+\.[0-9]{2})', items_text)
            
            for match in item_matches:
                item = {
                    "name": match.group(1).strip(),
                    "price": match.group(2)
                }
                # Try to extract quantity if present
                qty_match = re.search(r'(\d+)\s*x', item["name"])
                if qty_match:
                    item["quantity"] = qty_match.group(1)
                    item["name"] = re.sub(r'\d+\s*x\s*', '', item["name"]).strip()
                
                result["items"].append(item)
        
        return result