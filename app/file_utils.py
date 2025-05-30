import os
import logging
import json
import re
from datetime import datetime
import asyncio # Added
import aiohttp  # Added

# Configure logging (can be configured centrally if preferred)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PANTRY_BASE_URL = "https://getpantry.cloud/apiv1/pantry" # Added for Pantry

# --- Helper function to save output (NOW ASYNC for Pantry part) --- 
async def save_output_to_file_async(
    raw_blog_output=None, 
    raw_image_prompt=None, 
    raw_instagram_post_image_prompt=None, 
    raw_instagram_video_prompt=None,  # Added for video prompt
    parsed_package=None, 
    error=None, 
    slug='output',
    pantry_id=None # Added for Pantry integration
):
    """ 
    Saves the provided data locally to the 'answers' folder 
    and optionally to Pantry if a pantry_id is provided (Pantry part is async).
    """
    output_dir = "answers"
    counter_file = os.path.join(output_dir, "counter.txt")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_slug = re.sub(r'[^\w-]', '', slug)[:50]
    local_filename = None # Initialize local_filename

    # --- Get Username ---
    raw_username = os.getenv("WP_USERNAME", "unknown_user")
    # Sanitize username: allow alphanumeric, underscore, hyphen. Replace others.
    safe_username = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_username)
    if not safe_username: # If sanitization results in an empty string (e.g., username was all invalid chars)
        safe_username = "default_user"
    safe_username = safe_username[:30] # Limit length for extremely long usernames

    # --- Prepare data to save (common for local and cloud) ---
    # This section determines `next_count` for the local file's ID and filename prefix.
    # This count is also used as the 'id' within the JSON data.
    count = 0
    try:
        os.makedirs(output_dir, exist_ok=True) # Ensure answers dir exists
        with open(counter_file, 'r') as f_count:
            count = int(f_count.read().strip())
    except FileNotFoundError:
        logging.info(f"Counter file '{counter_file}' not found, starting count at 0.")
        count = 0
    except ValueError:
        logging.warning(f"Invalid content in {counter_file}. Resetting count to 0.")
        count = 0
    except Exception as e_read:
        logging.error(f"Error reading counter file {counter_file}: {e_read}. Resetting count.")
        count = 0
    
    next_count = count + 1
    
    data_to_save = {
        "id": next_count, # Using the local counter for the main ID
        "timestamp": timestamp,
        "status": "error" if error else "success",
        "error_message": error,
        "raw_blog_llm_output": raw_blog_output,
        "raw_image_prompt_llm_output": raw_image_prompt,
        "raw_instagram_post_image_prompt": raw_instagram_post_image_prompt,
        "raw_instagram_video_prompt": raw_instagram_video_prompt,
        "final_parsed_package": parsed_package,
        "pantry_basket_name": None # Will be populated if saved to Pantry
    }

    # --- 1. Attempt Local Save ---
    local_save_successful = False
    try:
        # Incorporate username into filename
        local_filename = os.path.join(output_dir, f"{safe_username}_{next_count:04d}_{safe_slug}_{timestamp}.json")
        with open(local_filename, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        logging.info(f"Successfully saved output locally to {local_filename}")
        
        # Try to update counter file only after successful local save of data
        try:
            with open(counter_file, 'w') as f_count:
                f_count.write(str(next_count))
        except Exception as e_write_counter:
            # Log error but don't fail the entire save if counter update fails
            logging.error(f"Failed to write next count ({next_count}) to {counter_file}: {e_write_counter}. Local data saved to {local_filename}.")
        
        local_save_successful = True

    except Exception as e_local_save:
        logging.exception(f"Failed to save output locally: {e_local_save}")
        # If local save fails, we might not want to proceed to Pantry,
        # or we might want to log this specific failure prominently.
        # For now, we'll just log and not attempt Pantry if local save fails.

    # --- 2. Attempt Pantry Save (if local save was successful and pantry_id is provided) ---
    if local_save_successful and pantry_id:
        # Use a descriptive basket name for Pantry, including the local ID and username for correlation
        pantry_basket_name = f"{safe_username}_{next_count:04d}_{safe_slug}_{timestamp}"
        # Create a copy of data_to_save to modify for Pantry if needed, 
        # or add pantry_basket_name to the original if it's acceptable for local save too.
        # For this version, let's add it to the main dict before local save, 
        # so it's also in the local file for reference.
        # (This was already done when data_to_save was defined with pantry_basket_name: None)
        data_to_save_for_pantry = data_to_save.copy() # Make a copy to add pantry basket name
        data_to_save_for_pantry["pantry_basket_name"] = pantry_basket_name

        try:
            async with aiohttp.ClientSession() as session:
                pantry_url = f"{PANTRY_BASE_URL}/{pantry_id}/basket/{pantry_basket_name}"
                headers = {"Content-Type": "application/json"}
                async with session.post(pantry_url, json=data_to_save_for_pantry, headers=headers) as response:
                    response.raise_for_status()
                    logging.info(f"Successfully saved output to Pantry. Basket: {pantry_basket_name}")
        except aiohttp.ClientResponseError as e: # More specific exception for aiohttp HTTP errors
            logging.error(f"Failed to save output to Pantry (Basket: {pantry_basket_name}): {e.status} - {e.message}")
            # response_text = await e.response.text() if hasattr(e, 'response') and e.response else "No response body"
            # logging.error(f"Pantry Error Response: {response_text}")
            logging.error(f"Pantry Error Response (from history): {e.history}") # history might be more informative
        except aiohttp.ClientError as e: # Catch other aiohttp client errors (e.g., connection issues)
             logging.error(f"AIOHTTP client error saving to Pantry (Basket: {pantry_basket_name}): {e}")
        except Exception as e_pantry_generic:
            logging.exception(f"An unexpected error occurred during Pantry save (Basket: {pantry_basket_name}): {e_pantry_generic}")
    elif pantry_id and not local_save_successful:
        logging.warning("Skipping Pantry save because local save failed.")
    elif not pantry_id:
        logging.info("Pantry ID not provided. Skipping Pantry save.")

# --- Pantry Loading Functions (NOW ASYNC) ---

async def list_pantry_baskets_async(pantry_id: str) -> list[str] | None:
    """Fetches the list of basket names from a given Pantry ID (async)."""
    if not pantry_id:
        logging.error("Pantry ID not provided for listing baskets.")
        return None
    try:
        url = f"{PANTRY_BASE_URL}/{pantry_id}" # Endpoint for pantry details
        headers = {"Content-Type": "application/json"} # Usually not needed for GET but good practice
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status() # Check for HTTP errors
                details = await response.json()
                
                baskets_data = details.get("baskets", [])
                basket_names = [basket.get("name") for basket in baskets_data if basket.get("name")]
                basket_names.sort() # Sort alphabetically, or consider sorting by a timestamp in name later
                
                logging.info(f"Successfully fetched {len(basket_names)} basket names from Pantry ID {pantry_id}.")
                return basket_names
    except aiohttp.ClientResponseError as http_err:
        logging.error(f"HTTP error fetching Pantry baskets for ID {pantry_id}: {http_err.status} - {http_err.message}")
        # response_text = await http_err.response.text() if hasattr(http_err, 'response') and http_err.response else "No response body"
        # logging.error(f"Pantry Error Response (listing details): {response_text}")
        return None
    except aiohttp.ClientError as req_err:
        logging.error(f"AIOHTTP client error fetching Pantry baskets for ID {pantry_id}: {req_err}")
        return None
    except json.JSONDecodeError as json_err:
        logging.error(f"Failed to decode JSON response when listing Pantry baskets for ID {pantry_id}: {json_err}.")
        return None
    except Exception as e_generic:
        logging.exception(f"An unexpected error occurred while listing Pantry baskets for ID {pantry_id}: {e_generic}")
        return None

async def get_pantry_basket_content_async(pantry_id: str, basket_name: str) -> dict | None:
    """Fetches the content of a specific basket from Pantry (async)."""
    if not pantry_id or not basket_name:
        logging.error("Pantry ID or basket name not provided for fetching content.")
        return None
    try:
        url = f"{PANTRY_BASE_URL}/{pantry_id}/basket/{basket_name}"
        headers = {"Content-Type": "application/json"} # As before
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status() # Check for HTTP errors
                
                basket_content = await response.json()
                logging.info(f"Successfully fetched content for basket '{basket_name}' from Pantry ID {pantry_id}.")
                return basket_content # This should be the full saved data structure
    except aiohttp.ClientResponseError as http_err:
        logging.error(f"HTTP error fetching content for Pantry basket '{basket_name}' (ID: {pantry_id}): {http_err.status} - {http_err.message}")
        # response_text = await http_err.response.text() if hasattr(http_err, 'response') and http_err.response else "No response body"
        # logging.error(f"Pantry Error Response (getting basket content): {response_text}")
        return None
    except aiohttp.ClientError as req_err:
        logging.error(f"AIOHTTP client error fetching content for Pantry basket '{basket_name}' (ID: {pantry_id}): {req_err}")
        return None
    except json.JSONDecodeError as json_err:
        logging.error(f"Failed to decode JSON response for Pantry basket '{basket_name}' (ID: {pantry_id}): {json_err}.")
        return None
    except Exception as e_generic:
        logging.exception(f"An unexpected error occurred while getting content for Pantry basket '{basket_name}' (ID: {pantry_id}): {e_generic}")
        return None

# Placeholder function remains the same
def extract_keywords(text):
    # ... (keep existing function body)
    logging.info(f"Keyword extraction requested for: {text[:50]}...")
    return ["keyword1", "keyword2"] 