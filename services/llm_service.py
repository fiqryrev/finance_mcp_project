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
        try:
            # Read the image file
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            # Create a multipart request with image
            image_part = Part.from_image(image_bytes)
            multipart_request = [prompt, image_part]
            
            # Generate response
            response = self.model.generate_content(multipart_request)
            return response.text
            
        except Exception as e:
            raise Exception(f"Error in LLM image processing: {str(e)}")
    
    async def analyze_text(self, text: str, system_prompt: Optional[str] = None) -> str:
        """
        Analyze text with the LLM
        
        Args:
            text: Text to analyze
            system_prompt: Optional system prompt
            
        Returns:
            LLM response as string
        """
        try:
            if system_prompt:
                # For models that support system prompts
                response = self.model.generate_content(
                    [system_prompt, text]
                )
            else:
                response = self.model.generate_content(text)
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Error in LLM text analysis: {str(e)}")
    
    async def analyze_financial_data(self, analysis_type: str) -> Dict[str, Any]:
        """
        Analyze financial data based on the requested analysis type
        
        Args:
            analysis_type: Type of analysis to perform (categories, trends, merchants, budget)
            
        Returns:
            Dictionary with analysis results
        """
        # Create appropriate prompt based on analysis type
        if analysis_type == "categories":
            prompt = """
            Analyze the spending categories in my financial data and provide insights.
            Focus on:
            1. Top spending categories
            2. Unusual or unexpected spending patterns
            3. Recommendations for budget adjustments
            4. Comparison with typical spending distributions
            """
        elif analysis_type == "trends":
            prompt = """
            Analyze the monthly trends in my financial data.
            Focus on:
            1. Month-over-month spending changes
            2. Seasonal patterns
            3. Growing or shrinking expense categories
            4. Unusual spikes or drops in spending
            """
        elif analysis_type == "merchants":
            prompt = """
            Analyze my spending across different merchants or vendors.
            Focus on:
            1. Top merchants by total spending
            2. Frequency of transactions per merchant
            3. Average transaction amount per merchant
            4. Recurring payments or subscriptions
            """
        elif analysis_type == "budget":
            prompt = """
            Analyze my budget status based on my financial data.
            Focus on:
            1. Categories where I'm over budget
            2. Categories where I have remaining budget
            3. Projected end-of-month status
            4. Recommendations for staying on budget
            """
        else:
            prompt = f"Please provide a general analysis of my financial data with focus on {analysis_type}."
        
        # This is a mockup response for now as we don't have actual data to analyze
        # In a real implementation, we would load data from sheets and include it in the prompt
        
        mock_analysis = {
            "categories": """
            Based on your recent transactions, your top spending categories are:
            
            1. Dining & Restaurants (32% of spending)
            2. Groceries (24% of spending)
            3. Transportation (15% of spending)
            4. Entertainment (10% of spending)
            
            Your restaurant spending is higher than average for your income bracket.
            Consider setting a dining budget to reduce expenses in this category.
            
            Your grocery spending is efficient and in line with recommendations.
            """,
            
            "trends": """
            Your monthly spending shows the following trends:
            
            - Overall spending increased by 12% compared to last month
            - Dining expenses have been steadily increasing for 3 months
            - Grocery spending decreased by 8% this month
            - Seasonal increase in entertainment spending (typical for this time of year)
            
            The continuous increase in dining expenses suggests reviewing this category
            for potential savings opportunities.
            """,
            
            "merchants": """
            Your top merchants by spending are:
            
            1. Whole Foods Market - $342 (6 transactions)
            2. Amazon - $267 (12 transactions)
            3. Starbucks - $124 (15 transactions)
            4. Netflix - $45 (3 monthly subscriptions)
            
            Your frequent small purchases at Starbucks add up to a significant amount.
            Consider using a rewards program or brewing coffee at home.
            """,
            
            "budget": """
            Budget Status:
            
            ✅ Groceries: 68% of monthly budget used (on track)
            ❌ Dining: 112% of monthly budget used (over budget)
            ✅ Transportation: 74% of monthly budget used (on track)
            ✅ Entertainment: 82% of monthly budget used (slightly high)
            
            You've exceeded your dining budget for this month. Consider adjusting
            your dining habits or reallocating budget from other categories.
            """
        }
        
        # In a real implementation, we would call the LLM with the prompt and data
        # response = await self.analyze_text(prompt + data_context)
        # return {"analysis": response}
        
        # For now, return mock analysis
        return {
            "analysis": mock_analysis.get(analysis_type, "Analysis not available for this type."),
            "visualization_url": None  # In a real implementation, this could be a generated chart URL
        }
    
    async def create_system_prompt(self, context: str) -> str:
        """
        Create a system prompt for the LLM based on the context
        
        Args:
            context: Context for the system prompt
            
        Returns:
            System prompt string
        """
        base_prompt = """
        You are a financial assistant specialized in analyzing receipts, invoices, and financial data.
        Your goal is to provide accurate, helpful information and insights.
        
        When analyzing documents:
        - Extract key information precisely (dates, amounts, merchants, etc.)
        - Structure the data in a clear, consistent format
        - Highlight any unusual or important elements
        
        When providing financial analysis:
        - Focus on factual observations rather than judgments
        - Offer specific, actionable recommendations
        - Present data in an easy-to-understand way
        - Compare with benchmarks or past behavior when relevant
        
        Maintain a professional, helpful tone throughout interactions.
        """
        
        # Combine base prompt with specific context
        system_prompt = f"{base_prompt}\n\nCurrent context: {context}"
        
        return system_prompt