"""
Enhanced utility functions for image preprocessing to improve OCR results
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import requests
from urllib.parse import urlparse
from io import BytesIO

class ImageProcessor:
    """
    Service for processing and optimizing images for OCR
    """
    
    @staticmethod
    async def read_image_from_uploaded_file(file_byte):
        """
        Read an image from uploaded file bytes
        
        Args:
            file_byte: Bytes of uploaded file
            
        Returns:
            PIL Image object or None if failed
        """
        try:
            image_file = Image.open(file_byte)
            return image_file
        except Exception as e:
            print(f"Error in read_image_from_uploaded_file(): {e}")
            return None

    @staticmethod
    def get_image_from_url(image_url):
        """
        Download and load an image from a URL
        
        Args:
            image_url: URL of the image
            
        Returns:
            PIL Image object
            
        Raises:
            Exception if download or processing fails
        """
        try:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
            return image
        except Exception as e:
            print(f"Error in get_image_from_url(): {e}")
            raise e

    @staticmethod
    def convert_image_to_bytes(image_file):
        """
        Convert a PIL Image to bytes
        
        Args:
            image_file: PIL Image object
            
        Returns:
            Image as bytes
        """
        image_bytes = BytesIO()
        if image_file.mode != "RGB":
            image_file = image_file.convert("RGB")
        image_file.save(image_bytes, format='JPEG')
        image_bytes = image_bytes.getvalue()
        return image_bytes
    
    @staticmethod
    def convert_image_rgb_to_image_grayscale(image_file):
        """
        Convert an RGB image to grayscale
        
        Args:
            image_file: PIL Image object or path to image file
            
        Returns:
            Grayscale PIL Image
        """
        if isinstance(image_file, str):
            image = Image.open(image_file)
        else:
            image = image_file
        image_grayscale = image.convert('L')
        return image_grayscale

    @staticmethod
    def get_file_name_from_image_url(image_url):
        """
        Extract filename from an image URL
        
        Args:
            image_url: URL of the image
            
        Returns:
            Filename with extension
        """
        path = urlparse(image_url).path
        file_name, extension = path.split('/')[-1].rsplit('.', 1) 
        return f"{file_name}.{extension}"

    @staticmethod
    def preprocess_image_for_ocr(image_file, output_path=None):
        """
        Preprocess an image to improve OCR results
        
        Args:
            image_file: PIL Image object or path to image file
            output_path: Path to save the processed image (optional)
            
        Returns:
            Path to processed image or preprocessed PIL Image object
        """
        # Load the image if a path was provided
        if isinstance(image_file, str):
            img = cv2.imread(image_file)
        else:
            # Convert PIL image to OpenCV format
            img = np.array(image_file)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to get a binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        if output_path:
            # Save the processed image
            cv2.imwrite(output_path, binary)
            return output_path
        else:
            # Convert back to PIL Image
            return Image.fromarray(binary)

    @staticmethod
    def enhance_image(image_file, output_path=None):
        """
        Enhance an image to improve contrast and sharpness
        
        Args:
            image_file: PIL Image object or path to image file
            output_path: Path to save the enhanced image (optional)
            
        Returns:
            Path to enhanced image or enhanced PIL Image object
        """
        # Open the image if a path was provided
        if isinstance(image_file, str):
            img = Image.open(image_file)
        else:
            img = image_file
        
        # Convert to grayscale
        img = img.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)  # Increase contrast
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)  # Increase sharpness
        
        # Apply Gaussian blur to reduce noise
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        
        if output_path:
            # Save the enhanced image
            img.save(output_path)
            return output_path
        else:
            return img

    @staticmethod
    def optimize_for_ocr(image_file, output_path=None):
        """
        Apply multiple optimizations to prepare an image for OCR
        
        Args:
            image_file: PIL Image object or path to image file
            output_path: Path to save the optimized image (optional)
            
        Returns:
            Optimized PIL Image object or path to optimized image
        """
        # Step 1: Load image if needed
        if isinstance(image_file, str):
            img = Image.open(image_file)
        else:
            img = image_file
        
        # Step 2: Resize if too large
        if max(img.size) > 1800:
            ratio = 1800 / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # Step 3: Convert to grayscale
        img = img.convert('L')
        
        # Step 4: Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # Step 5: Enhance sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)
        
        if output_path:
            # Save the optimized image
            img.save(output_path)
            return output_path
        else:
            return img