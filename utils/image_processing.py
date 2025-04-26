"""
Utility functions for image preprocessing to improve OCR results
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

def preprocess_image_for_ocr(image_path: str, output_path: str = None) -> str:
    """
    Preprocess an image to improve OCR results
    
    Args:
        image_path: Path to the input image
        output_path: Path to save the processed image (if None, uses a temporary file)
        
    Returns:
        Path to the processed image
    """
    # If no output path provided, create one based on input path
    if output_path is None:
        file_name, file_ext = os.path.splitext(image_path)
        output_path = f"{file_name}_processed{file_ext}"
    
    # Read the image with OpenCV
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to get a binary image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Save the processed image
    cv2.imwrite(output_path, binary)
    
    return output_path

def enhance_image(image_path: str, output_path: str = None) -> str:
    """
    Enhance an image using PIL to improve contrast and sharpness
    
    Args:
        image_path: Path to the input image
        output_path: Path to save the enhanced image (if None, uses a temporary file)
        
    Returns:
        Path to the enhanced image
    """
    # If no output path provided, create one based on input path
    if output_path is None:
        file_name, file_ext = os.path.splitext(image_path)
        output_path = f"{file_name}_enhanced{file_ext}"
    
    # Open the image with PIL
    with Image.open(image_path) as img:
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
        
        # Save the enhanced image
        img.save(output_path)
    
    return output_path

def deskew_image(image_path: str, output_path: str = None) -> str:
    """
    Deskew an image to straighten text for better OCR results
    
    Args:
        image_path: Path to the input image
        output_path: Path to save the deskewed image (if None, uses a temporary file)
        
    Returns:
        Path to the deskewed image
    """
    # If no output path provided, create one based on input path
    if output_path is None:
        file_name, file_ext = os.path.splitext(image_path)
        output_path = f"{file_name}_deskewed{file_ext}"
    
    # Read the image with OpenCV
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to get a binary image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find all contours
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the largest contour by area
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Fit a rotated rectangle to the largest contour
    rect = cv2.minAreaRect(largest_contour)
    angle = rect[2]
    
    # Determine the angle to rotate
    if angle < -45:
        angle = 90 + angle
    
    # Get the rotation matrix
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Perform the rotation
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # Save the deskewed image
    cv2.imwrite(output_path, rotated)
    
    return output_path

def resize_image(image_path: str, output_path: str = None, target_size: int = 1800) -> str:
    """
    Resize an image while maintaining aspect ratio
    
    Args:
        image_path: Path to the input image
        output_path: Path to save the resized image (if None, uses a temporary file)
        target_size: Target size for the longest dimension
        
    Returns:
        Path to the resized image
    """
    # If no output path provided, create one based on input path
    if output_path is None:
        file_name, file_ext = os.path.splitext(image_path)
        output_path = f"{file_name}_resized{file_ext}"
    
    # Open the image with PIL
    with Image.open(image_path) as img:
        # Calculate new dimensions while preserving aspect ratio
        width, height = img.size
        
        if width > height:
            new_width = target_size
            new_height = int(height * (target_size / width))
        else:
            new_height = target_size
            new_width = int(width * (target_size / height))
        
        # Resize the image with high quality
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Save the resized image
        img.save(output_path)
    
    return output_path

def optimize_for_ocr(image_path: str) -> str:
    """
    Apply a series of optimizations to an image to prepare it for OCR
    
    Args:
        image_path: Path to the input image
        
    Returns:
        Path to the optimized image
    """
    # Create temporary paths for intermediate steps
    file_name, file_ext = os.path.splitext(image_path)
    resized_path = f"{file_name}_resized{file_ext}"
    deskewed_path = f"{file_name}_deskewed{file_ext}"
    enhanced_path = f"{file_name}_enhanced{file_ext}"
    final_path = f"{file_name}_optimized{file_ext}"
    
    try:
        # Step 1: Resize to a reasonable size
        resized_path = resize_image(image_path, resized_path)
        
        # Step 2: Deskew the image
        deskewed_path = deskew_image(resized_path, deskewed_path)
        
        # Step 3: Enhance the image
        enhanced_path = enhance_image(deskewed_path, enhanced_path)
        
        # Step 4: Final preprocessing
        final_path = preprocess_image_for_ocr(enhanced_path, final_path)
        
        return final_path
        
    except Exception as e:
        print(f"Error optimizing image: {e}")
        # If optimization fails, return the original image
        return image_path
    finally:
        # Clean up intermediate files
        for path in [resized_path, deskewed_path, enhanced_path]:
            if os.path.exists(path) and path != final_path and path != image_path:
                try:
                    os.remove(path)
                except:
                    pass