# This file makes the 'app' directory a Python package 

# Configure logging centrally if not done in individual modules or main app script
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables at the package level if desired
from dotenv import load_dotenv
load_dotenv()

# Make key functions available when importing from the 'app' package
from .llm_clients import initialize_llm_clients
from .wordpress_handler import create_draft_post
from .content_generator import (
    generate_persian_blog_package,
    generate_image_prompt,
    generate_instagram_image_prompt,
    generate_instagram_image_prompt_for_video,
    generate_instagram_video_prompt,
    generate_instagram_post_texts,
    analyze_blog_for_instagram_inputs
)
from .file_utils import save_output_to_file_async, extract_keywords
from .utils import get_app_version # Example utility from the refactored utils.py

logging.info("App package initialized.")

__all__ = [
    "initialize_llm_clients",
    "create_draft_post",
    "generate_persian_blog_package",
    "generate_image_prompt",
    "generate_instagram_image_prompt",
    "generate_instagram_image_prompt_for_video",
    "generate_instagram_video_prompt",
    "generate_instagram_post_texts",
    "analyze_blog_for_instagram_inputs",
    "save_output_to_file_async",
    "extract_keywords",
    "get_app_version"
] 