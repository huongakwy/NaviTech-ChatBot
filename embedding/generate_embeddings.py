import numpy as np
from env import env
import os
from openai import OpenAI


def generate_embedding(text: str, retry_limit=3):
    """Generate embedding using OpenAI API"""
    if not text.strip():
        return np.zeros(env.LEN_EMBEDDING).tolist()
    
    client = OpenAI(api_key=env.OPENAI_API_KEY)
    
    retry_count = 0
    while retry_count < retry_limit:
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=env.LEN_EMBEDDING
            )
            
            if response and response.data:
                return response.data[0].embedding
            else:
                print(f"❌ No embeddings returned")
                return np.zeros(env.LEN_EMBEDDING).tolist()
                
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            retry_count += 1
            if retry_count < retry_limit:
                print(f"⚠️ Retrying... Attempt {retry_count}/{retry_limit}")
            continue
    
    print("❌ All retry attempts failed.")
    return np.zeros(env.LEN_EMBEDDING).tolist()


def query_embedding(text: str, retry_limit=3):
    """Generate query embedding using OpenAI API"""
    if not text.strip():
        return np.zeros(env.LEN_EMBEDDING).tolist()
    
    client = OpenAI(api_key=env.OPENAI_API_KEY)
    
    retry_count = 0
    while retry_count < retry_limit:
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=env.LEN_EMBEDDING
            )
            
            if response and response.data:
                return response.data[0].embedding
            else:
                print(f"❌ No embeddings returned")
                return np.zeros(env.LEN_EMBEDDING).tolist()
                
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            retry_count += 1
            if retry_count < retry_limit:
                print(f"⚠️ Retrying... Attempt {retry_count}/{retry_limit}")
            continue