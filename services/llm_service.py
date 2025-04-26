"""
Service for interacting with VertexAI LLMs (Gemini and Claude)
"""
import os
from typing import Dict, List, Any, Optional, Union
import vertexai
from vertexai.generative_models import GenerativeModel, Part

from config.config import VERTEX_PROJECT_ID, VERTEX_LOCATION, VERTEX_MODEL_ID

class LLMService:
    """Service for interacting with VertexAI LLMs"""
    
    def __init__(self, model_id: Optional[str] = None):
        """Initialize the LLM service"""
        self.project_id = VERTEX_PROJECT_ID
        self.location = VERTEX_LOCATION
        self.model_id = model_id or VERTEX_MODEL_ID
        
        # Initialize VertexAI
        vertexai.init(project=self.project_id, location=self.location)
        self.model = GenerativeModel(model_name=self.model_id)
    
    async def process_image(self, image_path: str, prompt: str) -> str:
        """
        Process an image with the LLM and return the response
        
        Args:
            image_path: Path to the image file
            prompt: Prompt to send to the LLM
            
        Returns:
            LLM response as string
        """
        # Read the image file
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # Create multipart request
        multipart_request = [
            prompt,
            Part.from_image(image_data)
        ]
        
        # Generate response
        response = self.model.generate_content(multipart_request)
        return response.text
    
    async def analyze_text(self, text: str, system_prompt: Optional[str] = None) -> str:
        """
        Analyze text with the LLM
        
        Args:
            text: Text to analyze
            system_prompt: Optional system prompt
            
        Returns:
            LLM response as string
        """
        if system_prompt:
            # For models that support system prompts
            response = self.model.generate_content(
                system_prompt,
                text
            )
        else:
            response = self.model.generate_content(text)
        
        return response.text
