import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- LLM Client Initialization Function ---
def initialize_llm_clients():
    llm_blog = None
    llm_image_prompt = None
    llm_instagram_text = None # Added new client
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    AVALAI_BASE_URL = "https://api.avalai.ir/v1"
    BLOG_MODEL_NAME = "gemini-2.5-pro-preview-05-06" # Updated model
    IMAGE_PROMPT_MODEL_NAME = "gpt-4.1" # Updated model
    INSTAGRAM_TEXT_MODEL_NAME = "gemini-2.5-flash-preview-04-17" # Updated model for Instagram texts
    TIMEOUT = 90

    if not GOOGLE_API_KEY:
        logging.warning("GOOGLE_API_KEY not found in environment variables. Cannot initialize LLM clients.")
        return None, None, None # Adjusted return
    
    try:
        logging.info(f"Initializing ChatOpenAI (Blog) with model='{BLOG_MODEL_NAME}', base_url='{AVALAI_BASE_URL}'...")
        llm_blog = ChatOpenAI(
            model_name=BLOG_MODEL_NAME,
            openai_api_key=GOOGLE_API_KEY,
            openai_api_base=AVALAI_BASE_URL,
            request_timeout=TIMEOUT,
        )
        logging.info("ChatOpenAI client (Blog) initialized successfully.")

        logging.info(f"Initializing ChatOpenAI (Image Prompt) with model='{IMAGE_PROMPT_MODEL_NAME}', base_url='{AVALAI_BASE_URL}'...")
        llm_image_prompt = ChatOpenAI(
            model_name=IMAGE_PROMPT_MODEL_NAME,
            openai_api_key=GOOGLE_API_KEY,
            openai_api_base=AVALAI_BASE_URL,
            request_timeout=TIMEOUT,
        )
        logging.info("ChatOpenAI client (Image Prompt) initialized successfully.")

        logging.info(f"Initializing ChatOpenAI (Instagram Text) with model='{INSTAGRAM_TEXT_MODEL_NAME}', base_url='{AVALAI_BASE_URL}'...") # New client initialization
        llm_instagram_text = ChatOpenAI(
            model_name=INSTAGRAM_TEXT_MODEL_NAME,
            openai_api_key=GOOGLE_API_KEY,
            openai_api_base=AVALAI_BASE_URL,
            request_timeout=TIMEOUT,
        )
        logging.info("ChatOpenAI client (Instagram Text) initialized successfully.")

    except Exception as e:
        logging.exception(f"Error initializing ChatOpenAI clients: {e}")
        llm_blog = None 
        llm_image_prompt = None
        llm_instagram_text = None # Ensure it's None on error
    
    return llm_blog, llm_image_prompt, llm_instagram_text # Adjusted return 