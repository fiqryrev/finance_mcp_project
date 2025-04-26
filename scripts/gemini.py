import io, re
from google.oauth2 import service_account
import vertexai
from mimetypes import guess_type
import time
import random
from typing import Any
import logging

from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmCategory,
    HarmBlockThreshold,
    Image
)

print('V2')
# Vertex AI configuration
project_id = 'paper-ds-production'
credentials_file_path = 'materials/skilled-compass.json'
credentials = service_account.Credentials.from_service_account_file(credentials_file_path)
vertexai.init(project=project_id, credentials=credentials)
model = "gemini-2.0-flash"
multimodal_model = GenerativeModel(model)

safety_config = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

# Generation Config
config = GenerationConfig(temperature=0.0, top_p=1, top_k=32)




def call_gemini(prompt, 
                max_retries=2, 
                initial_backoff=1.0, 
                max_backoff=60.0, 
                backoff_factor=2.0, 
                jitter=0.1):

    retries = 0
    backoff = initial_backoff
    last_exception = None
    
    while retries < max_retries:
        try:
            # Generate content using the multimodal model
            responses = multimodal_model.generate_content(
                [prompt],
                safety_settings=safety_config, 
                generation_config=config, 
                stream=True
            )
            
            # Collect the full result
            full_result = ''
            for response in responses:
                full_result += response.text
            
            return full_result.strip()
            
        except Exception as e:
            last_exception = e
            
            # Log the error
            if logging:
                logging.warning(f"Gemini API error on attempt {retries+1}/{max_retries}: {str(e)}")
            else:
                print(f"Gemini API error on attempt {retries+1}/{max_retries}: {str(e)}")
            
            # Check if we should retry based on the error type
            if "ServiceUnavailable: 503 Connection reset" in str(e) or "Connection reset" in str(e):
                # Calculate backoff with jitter
                jitter_value = backoff * jitter * random.random()
                wait_time = min(backoff + jitter_value, max_backoff)
                
                if logging:
                    logging.info(f"Retrying in {wait_time:.2f} seconds...")
                else:
                    print(f"Retrying in {wait_time:.2f} seconds...")
                
                time.sleep(wait_time)
                # Increase backoff exponentially
                backoff = min(backoff * backoff_factor, max_backoff)
                retries += 1
            else:
                # For other errors, raise immediately
                raise
    
    # If all retries failed
    error_msg = f"Failed to call Gemini API after {max_retries} attempts. Last error: {last_exception}"
    if logging:
        logging.error(error_msg)
    else:
        print(error_msg)
    
    raise Exception(error_msg)