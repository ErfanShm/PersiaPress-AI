import os
import logging
from dotenv import load_dotenv
import sys # Import sys for exit, if needed for any remaining utility
import json # Import json for JSON parsing, if needed for any remaining utility
from langchain_core.prompts import ChatPromptTemplate # Keep for message structure if needed, but not for chain

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Example of a utility function that could remain or be added here:
def get_app_version():
    return "1.0.0-refactored"

# Placeholder for any other common utilities that don't fit specific modules
# For example, a function to sanitize inputs or format dates if used across modules.

# Ensure that functions called by generate_persian_blog_package are imported if it were here,
# but since it's moved, this file no longer needs to directly manage those dependencies.

# The original file had many imports related to functions that have now been moved.
# We only keep imports necessary for any functions that *remain* in this utils.py.
# For example, `requests`, `base64`, `markdown`, `mimetypes` were for `create_draft_post` (now in wordpress_handler.py)
# `langchain_openai` and specific message types were for LLM calls (now in llm_clients.py and content_generator.py)
# `datetime` and `re` (for save_output_to_file) are now in file_utils.py

# If app.py or other modules need to access the refactored functions,
# they should now import them from their new locations, e.g.:
# from .llm_clients import initialize_llm_clients
# from .wordpress_handler import create_draft_post
# from .content_generator import generate_persian_blog_package
# from .file_utils import save_output_to_file

