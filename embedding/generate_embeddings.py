import numpy as np
from env import env
import os
from google.genai import types
from google import genai



# List of API keys
API_KEYS = [
    env.GEMINI_API_KEY,
    env.GEMINI_API_KEY1,
    env.GEMINI_API_KEY2
]

def generate_embedding(text: str, retry_limit=3):
    if not text.strip():
        return np.zeros(env.LEN_EMBEDDING).tolist()  # Return empty vector if text is empty
    
    retry_count = 0
    while retry_count < retry_limit:
        for api_index in range(len(API_KEYS)):
            try:
                # Initialize the API client
                client = genai.Client(api_key=API_KEYS[api_index])
                
                # Call the API to generate embeddings
                result = client.models.embed_content(
                    model="text-embedding-004",  # Updated model
                    contents=text,
                    config=types.EmbedContentConfig(output_dimensionality=env.LEN_EMBEDDING)
                )
                
                # Check if embeddings are returned and return the first result
                if result and result.embeddings:
                    return result.embeddings[0].values
                else:
                    print(f"❌ No embeddings returned for API key {api_index + 1}")
                    return np.zeros(env.LEN_EMBEDDING).tolist()  # Return empty vector if no embeddings
                
            except Exception as e:
                # Log the error and move to the next API key
                print(f"❌  Error with API key {api_index + 1}: {e}")
                continue
        
        retry_count += 1
        print(f"⚠️ Retrying... Attempt {retry_count}/{retry_limit}")
    
    # Return an empty vector if all retries fail
    print("❌ All retry attempts failed.")
    return np.zeros(env.LEN_EMBEDDING).tolist()


def query_embedding(text: str, retry_limit = 3):
    if not text.strip():
        return np.zeros(env.LEN_EMBEDDING).tolist()  # Return empty vector if text is empty
    
    retry_count = 0
    while retry_count < retry_limit:
        for api_index in range(len(API_KEYS)):
            try:
                # Initialize the API client
                client = genai.Client(api_key=API_KEYS[api_index])
                
                # Call the API to generate embeddings
                result = client.models.embed_content(
                    model="text-embedding-004",  # Updated model
                    contents=text,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_QUERY",
                        output_dimensionality=env.LEN_EMBEDDING  # ✅ Consistent 768 dims
                    )
                )
                
                # Check if embeddings are returned and return the first result
                if result and result.embeddings:
                    return result.embeddings[0].values
                else:
                    print(f"❌ No embeddings returned for API key {api_index + 1}")
                    return np.zeros(env.LEN_EMBEDDING).tolist()  # ✅ Fixed: 768 not 3072
                
            except Exception as e:
                # Log the error and move to the next API key
                print(f"❌ Error with API key {api_index + 1}: {e}")
                continue
        
        retry_count += 1
        print(f"⚠️ Retrying... Attempt {retry_count}/{retry_limit}")