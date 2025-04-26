"""
Utility functions for processing PDF documents
"""
import requests
import fitz  # PyMuPDF
from urllib.parse import urlparse
from PIL import Image
from io import BytesIO
import tempfile
import os

class PDFProcessor:
    """Service for processing PDF documents"""
    
    @staticmethod
    async def read_pdf_from_uploaded_file(file):
        """
        Read a PDF from uploaded file
        
        Args:
            file: Uploaded file
            
        Returns:
            BytesIO object containing PDF data or None if failed
        """
        try:
            pdf_file = BytesIO(await file.read())
            pdf_file.seek(0)  
            return pdf_file
        except Exception as e:
            print(f"Error in read_pdf_from_uploaded_file(): {e}")
            return None

    @staticmethod
    def get_pdf_from_url(pdf_url):
        """
        Download and load a PDF from a URL
        
        Args:
            pdf_url: URL of the PDF
            
        Returns:
            BytesIO object containing PDF data
            
        Raises:
            Exception if download or processing fails
        """
        try:
            response = requests.get(pdf_url)
            pdf_file = BytesIO(response.content) 
            pdf_file.seek(0)
            return pdf_file
        except Exception as e:
            print(f"Error in get_pdf_from_url(): {e}")
            raise e
    
    @staticmethod
    def convert_pdf_to_images(pdf_file, image_scale=4.0):
        """
        Convert PDF to list of images, one per page
        
        Args:
            pdf_file: Path to PDF file or BytesIO object containing PDF data
            image_scale: Scale factor for image quality (higher is better quality but larger)
            
        Returns:
            List of PIL Image objects, one per page
        """
        if isinstance(pdf_file, str):
            pdf = fitz.open(pdf_file) 
        else:
            pdf = fitz.open("pdf", pdf_file.read())

        images = [
            Image.open(BytesIO(page.get_pixmap(matrix=fitz.Matrix(image_scale, image_scale)).tobytes("jpg"))).convert('RGB')
            for page in pdf
        ]
        pdf.close()
        return images
    
    @staticmethod
    def save_images_to_temp_files(images, prefix="pdf_page_", format="PNG"):
        """
        Save list of images to temporary files
        
        Args:
            images: List of PIL Image objects
            prefix: Prefix for temporary filenames
            format: Image format to save as
            
        Returns:
            List of paths to saved image files
        """
        temp_files = []
        for i, img in enumerate(images):
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=f'.{format.lower()}', delete=False) as temp:
                temp_path = temp.name
                # Save the image
                img.save(temp_path, format=format)
                temp_files.append(temp_path)
        
        return temp_files
    
    @staticmethod
    def extract_text_from_pdf(pdf_file):
        """
        Extract text from PDF
        
        Args:
            pdf_file: Path to PDF file or BytesIO object containing PDF data
            
        Returns:
            Extracted text as string
        """
        if isinstance(pdf_file, str):
            pdf = fitz.open(pdf_file) 
        else:
            pdf_file.seek(0)  # Ensure we're at the beginning of the file
            pdf = fitz.open("pdf", pdf_file.read())
        
        text = ""
        for page in pdf:
            text += page.get_text()
        
        pdf.close()
        return text
    
    @staticmethod
    def pdf_to_text_and_images(pdf_file):
        """
        Process PDF into both text and images
        
        Args:
            pdf_file: Path to PDF file or BytesIO object containing PDF data
            
        Returns:
            Tuple of (text, list_of_images)
        """
        # Extract text
        if isinstance(pdf_file, str):
            pdf = fitz.open(pdf_file) 
        else:
            pdf_file.seek(0)
            pdf_bytes = pdf_file.read()
            pdf = fitz.open("pdf", pdf_bytes)
            pdf_file.seek(0)  # Reset for image extraction
        
        text = ""
        for page in pdf:
            text += page.get_text()
        
        pdf.close()
        
        # Extract images
        images = PDFProcessor.convert_pdf_to_images(pdf_file)
        
        return text, images
    
    @staticmethod
    def cleanup_temp_files(file_paths):
        """
        Clean up temporary files
        
        Args:
            file_paths: List of file paths to remove
        """
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception as e:
                print(f"Error removing temporary file {path}: {e}")