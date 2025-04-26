"""
Service for processing documents using LLM-based OCR
"""
import os
import re
import json
import copy
import logging
from typing import List, Dict, Any, Optional, Union
from io import BytesIO
import base64

# Google imports
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmCategory,
    HarmBlockThreshold,
    Image
)

# Local imports
from utils.timer import Timer
from utils.nominal_formatter import NominalFormatter
from utils.image_processing import ImageProcessor
from utils.pdf_processing import PDFProcessor
from prompts.prompt_multitype_invoices import PromptMultitypeInvoices

# Import environment variables
from dotenv import load_dotenv
load_dotenv()

class OCRService:
    """
    Service for processing documents using LLM-based OCR
    
    This service uses Google's Vertex AI with models like Gemini
    to extract structured data from images and PDFs.
    """
    
    def __init__(self, model="gemini-2.0-flash-lite-001"):
        """
        Initialize the OCR service
        
        Args:
            model: Name of the model to use
        """
        # Load configuration from environment variables
        self.credentials_file_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.project_id = os.getenv("PROJECT_ID")
        self.location = os.getenv("LOCATION", "us-central1")
        
        # Set model parameters
        self.model = model
        self.temperature = 0.0
        self.top_p = 1
        self.top_k = 1
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Vertex AI
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            vertexai.init(project=self.project_id, credentials=credentials, location=self.location)
            self.multimodal_model = GenerativeModel(self.model)
            
            # Configure safety settings
            self.safety_config = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Set generation config
            self.config = GenerationConfig(
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k
            )
            
            self.logger.info(f"OCR Service initialized with model: {model}")
        except Exception as e:
            self.logger.error(f"Error initializing OCR Service: {e}")
            raise

    ###--------------------- Helpers ---------------------###
    def extract_multimodal_responses(self, responses):
        """
        Extract and process the responses from the multimodal model
        
        Args:
            responses: Stream of responses from the model
            
        Returns:
            dict: Extracted data from responses
        """
        full_result = ''
        usage = {}
        
        # Collect all response text and usage metadata
        for response in responses:
            full_result += response.text
            
            # Extract usage metrics
            if hasattr(response, 'usage_metadata'):
                for i in str(response.usage_metadata).split('\n'):
                    if i.strip() and ':' in i:
                        key, value = i.split(':', 1)
                        value = value.strip()
                        try:
                            usage[key.strip()] = int(value)
                        except ValueError:
                            usage[key.strip()] = value
        
        # Extract JSON from response
        null = ''  # For use in eval
        match = re.search(r'\{.*\}', full_result, flags=re.DOTALL)
        if match:
            try:
                result = eval(match.group())
            except Exception as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                result = {"error": f"Failed to parse JSON response: {str(e)}"}
        else:
            self.logger.error("No valid JSON found in response")
            result = {"error": "No valid JSON found in response"}
        
        # Add usage metrics to result
        result.update({'usage': usage})
        return result

    def add_metadata_result(self, 
                          result: dict,
                          company_id: str = None,
                          client_ip: str = None,
                          file_url: str = None,
                          processed_ocr_date: str = None,
                          finished_ocr_date: str = None,
                          endpoint: str = None) -> dict:
        """
        Add metadata to OCR result
        
        Args:
            result: OCR result dictionary
            company_id: Company ID
            client_ip: Client IP address
            file_url: URL of processed file
            processed_ocr_date: Date when OCR processing started
            finished_ocr_date: Date when OCR processing finished
            endpoint: API endpoint used
            
        Returns:
            dict: Result with added metadata
        """
        result['metadata'] = {
            'company_id': company_id,
            'client_ip': client_ip,
            'file_url': file_url,
            'processed_ocr_date': processed_ocr_date,
            'finished_ocr_date': finished_ocr_date or Timer.get_current_time_iso(),
            'endpoint': endpoint,
            'model': self.model
        }
        return result

    ###--------------------- Main Interface Methods ---------------------###
    async def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process an image file to extract receipt/invoice data
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with extracted data
        """
        self.logger.info(f"Processing image: {image_path}")
        
        try:
            # Read the image file
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Process the image
            result = await self.process_document_from_image(
                image_bytes,
                document_type=None,  # Auto-detect type
                file_url=image_path
            )
            
            return result
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            return {"error": f"Failed to process image: {str(e)}"}

    async def process_document(self, document_path: str, file_ext: str) -> Dict[str, Any]:
        """
        Process a document file (image or PDF)
        
        Args:
            document_path: Path to the document file
            file_ext: File extension to determine processing method
            
        Returns:
            Dictionary with extracted data
        """
        self.logger.info(f"Processing document: {document_path}")
        
        try:
            # Read the file
            with open(document_path, 'rb') as f:
                file_bytes = f.read()
            
            # Determine file type and process accordingly
            if file_ext.lower() in ['.pdf']:
                return await self.process_document_from_pdf(
                    file_bytes,
                    document_type=None,  # Auto-detect type
                    file_url=document_path
                )
            else:
                return await self.process_document_from_image(
                    file_bytes,
                    document_type=None,  # Auto-detect type
                    file_url=document_path
                )
        except Exception as e:
            self.logger.error(f"Error processing document: {e}")
            return {"error": f"Failed to process document: {str(e)}"}

    ###--------------------- Document Classification ---------------------###
    async def classify_document_by_image(self,
                                       image_bytes: bytes,
                                       **metadata) -> Dict[str, Any]:
        """
        Classify document type from image
        
        Args:
            image_bytes: Image content as bytes
            **metadata: Additional metadata to include in result
            
        Returns:
            dict: Classification result
        """
        self.logger.info("Classifying document from image")
        start_time = Timer.timestamp_ms()
        
        prompt = PromptMultitypeInvoices.PROMPT_BASE_CLASSIFY_MULTITYPE_INVOICES
        
        # Preprocess the image
        try:
            # Convert bytes to image
            image = await ImageProcessor.read_image_from_uploaded_file(BytesIO(image_bytes))
            
            # Optimize image for OCR
            optimized_image = ImageProcessor.optimize_for_ocr(image)
            
            # Convert back to bytes
            optimized_bytes = ImageProcessor.convert_image_to_bytes(optimized_image)
            
            # Create content for model
            contents = [Image.from_bytes(optimized_bytes), prompt]
            
            # Generate content from model
            responses = self.multimodal_model.generate_content(
                contents,
                safety_settings=self.safety_config,
                generation_config=self.config,
                stream=True
            )
            
            # Extract and process responses
            result = self.extract_multimodal_responses(responses)
            
            # Add processing time
            processing_time = Timer.calculate_processing_time(start_time)
            result['processing_time_ms'] = processing_time
            
            # Add metadata
            final_result = self.add_metadata_result(
                result=result,
                processed_ocr_date=Timer.get_current_time_iso(),
                **metadata
            )
            
            self.logger.info(f"Document classification completed in {Timer.format_processing_time(processing_time)}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error classifying document: {e}")
            return {
                "error": f"Failed to classify document: {str(e)}",
                "processing_time_ms": Timer.calculate_processing_time(start_time)
            }

    async def classify_document_by_pdf(self,
                                     pdf_bytes: bytes,
                                     **metadata) -> Dict[str, Any]:
        """
        Classify document type from PDF
        
        Args:
            pdf_bytes: PDF content as bytes
            **metadata: Additional metadata to include in result
            
        Returns:
            dict: Classification result
        """
        self.logger.info("Classifying document from PDF")
        start_time = Timer.timestamp_ms()
        
        prompt = PromptMultitypeInvoices.PROMPT_BASE_CLASSIFY_MULTITYPE_INVOICES
        
        try:
            # Create PDF BytesIO
            pdf_io = BytesIO(pdf_bytes)
            
            # Extract text from PDF
            text = PDFProcessor.extract_text_from_pdf(pdf_io)
            
            # Check if we have sufficient text content
            if len(text.strip()) > 100:
                # Use text-based classification if we have enough text
                contents = [text, prompt]
                
                # Generate content from model
                responses = self.multimodal_model.generate_content(
                    contents,
                    safety_settings=self.safety_config,
                    generation_config=self.config,
                    stream=True
                )
                
                # Extract and process responses
                result = self.extract_multimodal_responses(responses)
            else:
                # If text content is insufficient, fall back to image-based classification
                # Convert first page to image
                pdf_io.seek(0)
                images = PDFProcessor.convert_pdf_to_images(pdf_io)
                
                if not images:
                    raise ValueError("Could not extract images from PDF")
                
                # Use the first page for classification
                first_page_bytes = ImageProcessor.convert_image_to_bytes(images[0])
                contents = [Image.from_bytes(first_page_bytes), prompt]
                
                # Generate content from model
                responses = self.multimodal_model.generate_content(
                    contents,
                    safety_settings=self.safety_config,
                    generation_config=self.config,
                    stream=True
                )
                
                # Extract and process responses
                result = self.extract_multimodal_responses(responses)
            
            # Add processing time
            processing_time = Timer.calculate_processing_time(start_time)
            result['processing_time_ms'] = processing_time
            
            # Add metadata
            final_result = self.add_metadata_result(
                result=result,
                processed_ocr_date=Timer.get_current_time_iso(),
                **metadata
            )
            
            self.logger.info(f"Document classification from PDF completed in {Timer.format_processing_time(processing_time)}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error classifying document from PDF: {e}")
            return {
                "error": f"Failed to classify document from PDF: {str(e)}",
                "processing_time_ms": Timer.calculate_processing_time(start_time)
            }

    ###--------------------- Document Processing ---------------------###
    def create_prompt_for_document_type(self, document_type: str = None) -> str:
        """
        Create appropriate prompt based on document type
        
        Args:
            document_type: Type of document to process
            
        Returns:
            str: Prompt for the specified document type
        """
        prompt = PromptMultitypeInvoices.PROMPT_BASE_PROCESS_MULTITYPE_INVOICES
        
        # Map document types to their output prompts
        prompt_output_map = {
            'invoice': PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE,
            'receipt': PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE,
            'sales_order': PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE,
            'purchase_order': PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE,
            'delivery_order': PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE,
            'goods_receipt': PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE,
            'sales_receipt': PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE,
            'purchase_receipt': PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE,
            'other': PromptMultitypeInvoices.PROMPT_OUTPUT_OTHER
        }
        
        # Add output format to prompt if document type is known
        if document_type in prompt_output_map:
            prompt = f"{prompt} {prompt_output_map[document_type]}"
        else:
            # Default to generic invoice format if unknown
            prompt = f"{prompt} {PromptMultitypeInvoices.PROMPT_OUTPUT_INVOICE}"
        
        return prompt

    async def process_document_from_image(self, 
                                        image_bytes: bytes,
                                        document_type: str = None, 
                                        **metadata) -> Dict[str, Any]:
        """
        Process document from image
        
        Args:
            image_bytes: Image content as bytes
            document_type: Type of document to process
            **metadata: Additional metadata to include in result
            
        Returns:
            dict: Processed document data
        """
        self.logger.info(f"Processing document from image, type: {document_type or 'unknown'}")
        start_time = Timer.timestamp_ms()
        
        # Create appropriate prompt
        prompt = self.create_prompt_for_document_type(document_type)
        
        try:
            # Convert bytes to image
            image = await ImageProcessor.read_image_from_uploaded_file(BytesIO(image_bytes))
            
            # Optimize image for OCR
            optimized_image = ImageProcessor.optimize_for_ocr(image)
            
            # Convert back to bytes
            optimized_bytes = ImageProcessor.convert_image_to_bytes(optimized_image)
            
            # Create content for model
            contents = [Image.from_bytes(optimized_bytes), prompt]
            
            # Generate content from model
            responses = self.multimodal_model.generate_content(
                contents,
                safety_settings=self.safety_config,
                generation_config=self.config,
                stream=True
            )
            
            # Extract and process responses
            result = self.extract_multimodal_responses(responses)
            
            # Format nominal values
            result = NominalFormatter.format_all_nominal_fields(result)
            
            # Add processing time
            processing_time = Timer.calculate_processing_time(start_time)
            result['processing_time_ms'] = processing_time
            
            # Add metadata
            final_result = self.add_metadata_result(
                result=result,
                processed_ocr_date=Timer.get_current_time_iso(),
                **metadata
            )
            
            self.logger.info(f"Document processing completed in {Timer.format_processing_time(processing_time)}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error processing document from image: {e}")
            return {
                "error": f"Failed to process document from image: {str(e)}",
                "processing_time_ms": Timer.calculate_processing_time(start_time)
            }

    async def process_document_from_pdf(self, 
                                      pdf_bytes: bytes,
                                      document_type: str = None,
                                      **metadata) -> Dict[str, Any]:
        """
        Process document from PDF
        
        Args:
            pdf_bytes: PDF content as bytes
            document_type: Type of document to process
            **metadata: Additional metadata to include in result
            
        Returns:
            dict: Processed document data
        """
        self.logger.info(f"Processing document from PDF, type: {document_type or 'unknown'}")
        start_time = Timer.timestamp_ms()
        
        # Create appropriate prompt
        prompt = self.create_prompt_for_document_type(document_type)
        
        try:
            # Create PDF BytesIO
            pdf_io = BytesIO(pdf_bytes)
            
            # Extract text and images from PDF
            text, images = PDFProcessor.pdf_to_text_and_images(pdf_io)
            
            # Decide whether to use text or image-based processing
            if len(text.strip()) > 200:  # Use text if we have enough content
                # Process document using extracted text
                contents = [text, prompt]
                
                # Generate content from model
                responses = self.multimodal_model.generate_content(
                    contents,
                    safety_settings=self.safety_config,
                    generation_config=self.config,
                    stream=True
                )
                
                # Extract and process responses
                result = self.extract_multimodal_responses(responses)
            else:
                # Fall back to image-based processing if text is insufficient
                if not images:
                    raise ValueError("Could not extract images from PDF")
                
                # Process all pages and merge results
                all_results = []
                for i, image in enumerate(images):
                    self.logger.info(f"Processing PDF page {i+1}/{len(images)}")
                    
                    # Optimize image for OCR
                    optimized_image = ImageProcessor.optimize_for_ocr(image)
                    
                    # Convert to bytes
                    image_bytes = ImageProcessor.convert_image_to_bytes(optimized_image)
                    
                    # Create content for model
                    contents = [Image.from_bytes(image_bytes), prompt]
                    
                    # Generate content from model
                    responses = self.multimodal_model.generate_content(
                        contents,
                        safety_settings=self.safety_config,
                        generation_config=self.config,
                        stream=True
                    )
                    
                    # Extract and process responses
                    page_result = self.extract_multimodal_responses(responses)
                    all_results.append(page_result)
                
                # Merge results from all pages
                result = self._merge_multi_page_results(all_results)
            
            # Format nominal values
            result = NominalFormatter.format_all_nominal_fields(result)
            
            # Add processing time
            processing_time = Timer.calculate_processing_time(start_time)
            result['processing_time_ms'] = processing_time
            
            # Add metadata
            final_result = self.add_metadata_result(
                result=result,
                processed_ocr_date=Timer.get_current_time_iso(),
                **metadata
            )
            
            self.logger.info(f"Document processing from PDF completed in {Timer.format_processing_time(processing_time)}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error processing document from PDF: {e}")
            return {
                "error": f"Failed to process document from PDF: {str(e)}",
                "processing_time_ms": Timer.calculate_processing_time(start_time)
            }

    def _merge_multi_page_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results from multiple pages into a single result
        
        Args:
            results: List of results from individual pages
            
        Returns:
            dict: Merged result
        """
        if not results:
            return {"error": "No results to merge"}
        
        # Use first result as base
        merged_result = copy.deepcopy(results[0])
        
        # Extract document type
        document_type = merged_result.get('document_type', 'unknown')
        
        # Handle different document types
        if document_type == 'sales_invoice' and 'sales_invoices' in merged_result:
            # Merge sales_invoices data
            all_sales_invoices = []
            for result in results:
                if 'sales_invoices' in result and result['sales_invoices']:
                    all_sales_invoices.extend(result['sales_invoices'])
            merged_result['sales_invoices'] = all_sales_invoices
            
        elif document_type == 'purchase_invoice' and 'purchase_invoices' in merged_result:
            # Merge purchase_invoices data
            all_purchase_invoices = []
            for result in results:
                if 'purchase_invoices' in result and result['purchase_invoices']:
                    all_purchase_invoices.extend(result['purchase_invoices'])
            merged_result['purchase_invoices'] = all_purchase_invoices
            
        elif document_type == 'product' and 'products' in merged_result:
            # Merge products data
            all_products = []
            for result in results:
                if 'products' in result and result['products']:
                    all_products.extend(result['products'])
            merged_result['products'] = all_products
            
        elif document_type == 'partner' and 'partners' in merged_result:
            # Merge partners data
            all_partners = []
            for result in results:
                if 'partners' in result and result['partners']:
                    all_partners.extend(result['partners'])
            merged_result['partners'] = all_partners
            
        elif 'items' in merged_result:
            # For generic invoice, merge items
            all_items = []
            for result in results:
                if 'items' in result and result['items']:
                    all_items.extend(result['items'])
            merged_result['items'] = all_items
        
        # Merge usage data from all results
        total_usage = {}
        for result in results:
            if 'usage' in result:
                for key, value in result['usage'].items():
                    if isinstance(value, (int, float)):
                        total_usage[key] = total_usage.get(key, 0) + value
                    else:
                        total_usage[key] = value
        
        merged_result['usage'] = total_usage
        
        return merged_result
    
    async def process_multiple_images(self,
                                   image_bytes_list: List[bytes],
                                   document_type: str = None,
                                   **metadata) -> Dict[str, Any]:
        """
        Process multiple images as a single document
        
        Args:
            image_bytes_list: List of image contents as bytes
            document_type: Type of document to process
            **metadata: Additional metadata to include in result
            
        Returns:
            dict: Processed document data
        """
        self.logger.info(f"Processing document from {len(image_bytes_list)} images, type: {document_type or 'unknown'}")
        start_time = Timer.timestamp_ms()
        
        try:
            # First, classify if document_type is not provided
            if not document_type:
                classification = await self.classify_document_by_image(image_bytes_list[0])
                if 'error' not in classification:
                    document_type = classification.get('document_type')
                    self.logger.info(f"Classified document as: {document_type}")
                else:
                    self.logger.warning("Document classification failed, proceeding with unknown type")
            
            # Create appropriate prompt
            prompt = self.create_prompt_for_document_type(document_type)
            
            # Process each image and collect results
            all_results = []
            for i, image_bytes in enumerate(image_bytes_list):
                self.logger.info(f"Processing image {i+1}/{len(image_bytes_list)}")
                
                # Convert bytes to image
                image = await ImageProcessor.read_image_from_uploaded_file(BytesIO(image_bytes))
                
                # Optimize image for OCR
                optimized_image = ImageProcessor.optimize_for_ocr(image)
                
                # Convert back to bytes
                optimized_bytes = ImageProcessor.convert_image_to_bytes(optimized_image)
                
                # Create content for model
                contents = [Image.from_bytes(optimized_bytes), prompt]
                
                # Generate content from model
                responses = self.multimodal_model.generate_content(
                    contents,
                    safety_settings=self.safety_config,
                    generation_config=self.config,
                    stream=True
                )
                
                # Extract and process responses
                page_result = self.extract_multimodal_responses(responses)
                all_results.append(page_result)
            
            # Merge results from all images
            result = self._merge_multi_page_results(all_results)
            
            # Format nominal values
            result = NominalFormatter.format_all_nominal_fields(result)
            
            # Add processing time
            processing_time = Timer.calculate_processing_time(start_time)
            result['processing_time_ms'] = processing_time
            
            # Add metadata
            final_result = self.add_metadata_result(
                result=result,
                processed_ocr_date=Timer.get_current_time_iso(),
                **metadata
            )
            
            self.logger.info(f"Multi-image document processing completed in {Timer.format_processing_time(processing_time)}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error processing multiple images: {e}")
            return {
                "error": f"Failed to process multiple images: {str(e)}",
                "processing_time_ms": Timer.calculate_processing_time(start_time)
            }