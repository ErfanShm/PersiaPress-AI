import os
import logging
import base64
import json
import requests
import markdown
import mimetypes
from dotenv import load_dotenv

# Load environment variables for WP_URL etc.
load_dotenv()

# Configure logging (can be configured centrally if preferred)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- WordPress Interaction Function ---
def create_draft_post(title: str, 
                      content: str, 
                      slug: str | None = None, 
                      tag_names: list[str] | None = None, # Accept tag names
                      primary_focus_keyword: str | None = None, # Add primary keyword
                      secondary_focus_keyword: str | None = None, # Add secondary keyword
                      additional_focus_keywords: list[str] | None = None, # Add additional keywords
                      seo_title: str | None = None,           # Add SEO Title
                      seo_description: str | None = None,   # Add SEO Description
                      image_path: str | None = None,        # Add local image path
                      image_alt_text: str | None = None     # Add image alt text
                      ) -> dict:
    """
    Creates a new draft post in WordPress using a multi-step process:
    1. Creates the post with basic info (title, content, status, slug, category, tags).
    2. Updates Rank Math fields (Focus Keywords, SEO Title, SEO Description) using the custom plugin endpoint.
    3. (If image_path provided) Uploads the image to the Media Library and sets it as the Featured Image.
    
    - Converts incoming markdown content to HTML.
    - Hardcodes Category ID 26 ('اخبار').
    - Handles tags: Searches for existing tags by name, creates new *ASCII* tags,
      adds default tag ID 46 ('اخبار هوش مصنوعی').
    
    Args:
        title (str): The title of the post (also used as default SEO title if seo_title not provided).
        content (str): The content of the post (as Markdown).
        slug (str | None, optional): The desired slug for the post.
        tag_names (list[str] | None, optional): List of tag names to assign/create.
        primary_focus_keyword (str | None, optional): The primary Rank Math focus keyword.
        secondary_focus_keyword (str | None, optional): The secondary Rank Math focus keyword.
        additional_focus_keywords (list[str] | None, optional): List of additional Rank Math focus keywords.
        seo_title (str | None, optional): The SEO title for Rank Math.
        seo_description (str | None, optional): The SEO description for Rank Math.
        image_path (str | None, optional): The absolute path to the local image file to upload.
        image_alt_text (str | None, optional): The alt text for the image (required if image_path is provided).

    Returns:
        dict: Contains 'success': bool and either 'data': dict (WP API response from CREATE)
              or 'error': str.
    """
    WP_URL = os.getenv("WP_URL")
    WP_USERNAME = os.getenv("WP_USERNAME")
    WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

    if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
        error_msg = "WordPress credentials not found in environment variables."
        logging.error(error_msg)
        return {"success": False, "error": error_msg}

    credentials = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode())
    headers = {
        'Authorization': f'Basic {token.decode("utf-8")}',
        'Content-Type': 'application/json'
    }
    base_api_url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2"
    posts_endpoint = f"{base_api_url}/posts"
    tags_endpoint = f"{base_api_url}/tags"
    media_endpoint = f"{base_api_url}/media" # Add media endpoint
    rank_math_endpoint = f"{WP_URL.rstrip('/')}/wp-json/rank-math-api/v1/update-meta"
    
    # Convert Markdown to HTML
    try:
        html_content = markdown.markdown(content)
    except Exception as md_err:
        logging.error(f"Error converting Markdown to HTML: {md_err}. Sending raw content.")
        html_content = content 

    # --- Process Tags --- 
    final_tag_ids = {46} # Start with default tag ID 'اخبار هوش مصنوعی', use set for uniqueness
    if tag_names and isinstance(tag_names, list):
        for name in tag_names:
            if not name or not isinstance(name, str):
                logging.warning(f"Skipping invalid tag name: {name}")
                continue
            
            try:
                # 1. Search for existing tag
                logging.info(f"Searching for tag ID for name: '{name}'")
                search_params = {'search': name, 'per_page': 1}
                response_search = requests.get(tags_endpoint, headers=headers, params=search_params, timeout=15)
                response_search.raise_for_status()
                search_results = response_search.json()

                found_tag = False
                if search_results and isinstance(search_results, list): 
                    # Check if exact match (WP search can be broad)
                    for tag_data in search_results:
                        if tag_data.get('name') == name:
                            tag_id = tag_data.get('id')
                            if tag_id:
                                logging.info(f"Found existing tag ID {tag_id} for name '{name}'")
                                final_tag_ids.add(tag_id)
                                found_tag = True
                                break # Found exact match

                # 2. If not found, try to create *if ASCII*
                if not found_tag:
                    logging.info(f"Tag '{name}' not found.")
                    if name.isascii():
                        logging.info(f"Attempting to create new ASCII tag: '{name}'")
                        create_tag_data = {'name': name}
                        response_create_tag = requests.post(tags_endpoint, headers=headers, json=create_tag_data, timeout=15)
                        
                        if response_create_tag.status_code == 201: # Created
                            new_tag_data = response_create_tag.json()
                            new_tag_id = new_tag_data.get('id')
                            if new_tag_id:
                                logging.info(f"Successfully created new tag '{name}' with ID {new_tag_id}")
                                final_tag_ids.add(new_tag_id)
                            else:
                                logging.error(f"Tag creation for '{name}' succeeded but no ID returned. Response: {new_tag_data}")
                        else:
                            error_detail = f"Failed to create tag '{name}'. Status: {response_create_tag.status_code}"
                            try: error_detail += f" | API Response: {json.dumps(response_create_tag.json())}"
                            except json.JSONDecodeError: error_detail += f" | API Response Text: {response_create_tag.text}" 
                            logging.error(error_detail)
                    else:
                        logging.warning(f"Skipping creation of non-ASCII tag: '{name}'")

            except requests.exceptions.RequestException as tag_e:
                logging.error(f"Error processing tag '{name}': {tag_e}")
            except Exception as tag_gen_e:
                logging.exception(f"Unexpected error processing tag '{name}': {tag_gen_e}")

    # --- Step 1: Create Post --- 
    create_data = {
        'title': title,
        'content': html_content,
        'status': 'draft',
        'categories': [26], # Hardcode Category ID 'اخبار'
        'tags': list(final_tag_ids) # Convert set back to list for JSON        
    }
    if slug:
        create_data['slug'] = slug

    new_post_id = None
    create_response_json = None
    
    try:
        logging.info(f"Step 1: Attempting to create WordPress draft: '{title[:50]}...' with Cat=[26], Tags={create_data.get('tags')}")
        response_create = requests.post(posts_endpoint, headers=headers, json=create_data, timeout=30)
        response_create.raise_for_status()
        create_response_json = response_create.json()
        new_post_id = create_response_json.get('id')
        logging.info(f"Step 1: Draft post created successfully! ID: {new_post_id}")
        if not new_post_id:
             raise ValueError("Failed to get new post ID from creation response.")
    except requests.exceptions.RequestException as e:
        error_detail = f"Error during Step 1 (Create Post): {e}"
        if e.response is not None:
            try: error_detail += f" | API Response: {json.dumps(e.response.json())}"
            except json.JSONDecodeError: error_detail += f" | API Response Text: {e.response.text}"
        logging.error(error_detail)
        return {"success": False, "error": error_detail}
    except Exception as e_general:
        error_msg = f"An unexpected error occurred during Step 1 (Create Post): {e_general}"
        logging.exception(error_msg)
        return {"success": False, "error": error_msg}

    # --- Step 2: Update Rank Math Fields via Custom Endpoint (if applicable) --- 
    keywords_list = []
    if primary_focus_keyword:
        keywords_list.append(primary_focus_keyword)
    if secondary_focus_keyword:
        keywords_list.append(secondary_focus_keyword)
    if additional_focus_keywords and isinstance(additional_focus_keywords, list):
        keywords_list.extend([kw for kw in additional_focus_keywords if isinstance(kw, str) and kw]) # Add valid additional keywords
    
    focus_keywords_to_send = ",".join(keywords_list) if keywords_list else None

    # Determine if any Rank Math update is needed
    meta_update_needed = bool(focus_keywords_to_send or seo_title or seo_description)

    if new_post_id and meta_update_needed:
        update_data = {
            'post_id': new_post_id
            # Conditionally add fields only if they have a value
        }
        if focus_keywords_to_send:
            update_data['rank_math_focus_keyword'] = focus_keywords_to_send
        if seo_title:
            update_data['rank_math_title'] = seo_title
        if seo_description:
            update_data['rank_math_description'] = seo_description
            
        # Only proceed if there's actually data to send
        if len(update_data) > 1: # Check if more than just post_id is present
            try:
                logging.info(f"Step 2: Attempting to update Rank Math field(s) for post ID {new_post_id} via custom endpoint {rank_math_endpoint}. Data: { {k: v for k, v in update_data.items() if k != 'post_id'} }...") # Log sent data
                response_update = requests.post(rank_math_endpoint, headers=headers, json=update_data, timeout=30)
                response_update.raise_for_status() # Check for HTTP errors (like 404, 500)
                
                update_result = response_update.json() 
                # Check the 'success' field within the custom endpoint's JSON response
                if update_result.get('success'):
                    logging.info(f"Step 2: Rank Math field update API call successful for post ID {new_post_id}. Response: {update_result}")
                else:
                     logging.error(f"Step 2: Rank Math field update failed for post ID {new_post_id} according to custom endpoint response. Response: {update_result}")
                     # You might still return overall success here, as the post was created.

            except requests.exceptions.RequestException as e:
                error_detail = f"Error during Step 2 (Update Rank Math Field(s) for Post {new_post_id}): {e}"
                if e.response is not None:
                    # Log specific error details from the response
                    try: error_detail += f" | Status: {e.response.status_code} | API Response: {json.dumps(e.response.json())}"
                    except json.JSONDecodeError: error_detail += f" | Status: {e.response.status_code} | API Response Text: {e.response.text}"
                    # Specifically check for 404 Not Found
                    if e.response.status_code == 404:
                        error_detail += " (Ensure the Rank Math API Manager Extended plugin is installed, activated, and the endpoint URL is correct)"
                logging.error(error_detail)
                # Log error but still return overall success as post was created
            except json.JSONDecodeError as json_e:
                 logging.error(f"Step 2: Failed to decode JSON response from custom endpoint for post ID {new_post_id}. Response text: {response_update.text}. Error: {json_e}")
                 # Log error but still return overall success
            except Exception as e_general:
                error_msg = f"An unexpected error occurred during Step 2 (Update Rank Math Field(s) for Post {new_post_id}): {e_general}"
                logging.exception(error_msg)
                # Log error but still return overall success
            
    # --- Step 3: Upload Image and Set as Featured Image (if path provided) ---
    if new_post_id and image_path and image_alt_text:
        if not os.path.exists(image_path):
            logging.warning(f"Step 3: Image path provided ({image_path}) but file does not exist. Skipping featured image.")
        else:
            try:
                # Determine filename and content type
                image_filename = os.path.basename(image_path)
                mime_type, _ = mimetypes.guess_type(image_path)
                if not mime_type:
                    mime_type = 'application/octet-stream' # Default if type cannot be guessed
                    logging.warning(f"Could not guess mime type for {image_filename}, using default: {mime_type}")

                logging.info(f"Step 3a: Attempting to upload image '{image_filename}' ({mime_type}) to Media Library for post {new_post_id}...")

                # Read image file content
                with open(image_path, 'rb') as img_file:
                    image_data = img_file.read()

                # Set headers specifically for media upload
                media_headers = {
                    'Authorization': headers['Authorization'], # Reuse token
                    'Content-Type': mime_type,
                    'Content-Disposition': f'attachment; filename="{image_filename}"'
                }

                # Upload the media
                response_media = requests.post(media_endpoint, headers=media_headers, data=image_data, timeout=60) # Increased timeout for upload
                response_media.raise_for_status()
                media_data = response_media.json()
                media_id = media_data.get('id')

                if media_id:
                    logging.info(f"Step 3a: Image uploaded successfully! Media ID: {media_id}")

                    # Step 3b: Update the post to set the featured media
                    logging.info(f"Step 3b: Setting Media ID {media_id} as featured image for Post ID {new_post_id}...")
                    update_post_data = {'featured_media': media_id}
                    # Also update alt text for the media item itself
                    update_media_alt_data = {'alt_text': image_alt_text}

                    # Update Media Alt Text
                    try:
                        media_item_endpoint = f"{media_endpoint}/{media_id}"
                        response_update_media = requests.post(media_item_endpoint, headers=headers, json=update_media_alt_data, timeout=30)
                        response_update_media.raise_for_status()
                        logging.info(f"Successfully updated alt text for Media ID {media_id}.")
                    except requests.exceptions.RequestException as e_media_alt:
                         logging.error(f"Error updating alt text for Media ID {media_id}: {e_media_alt}")
                         # Continue anyway to set featured image


                    # Set Featured Image on Post
                    post_update_endpoint = f"{posts_endpoint}/{new_post_id}"
                    response_update_post = requests.post(post_update_endpoint, headers=headers, json=update_post_data, timeout=30)
                    response_update_post.raise_for_status()
                    logging.info(f"Step 3b: Successfully set featured image for Post ID {new_post_id}.")

                else:
                    logging.error(f"Step 3a: Image upload failed for '{image_filename}'. No Media ID returned. Response: {media_data}")

            except FileNotFoundError:
                logging.error(f"Step 3: Error - Image file not found at path: {image_path}")
            except IOError as io_err:
                 logging.error(f"Step 3: Error reading image file {image_path}: {io_err}")
            except requests.exceptions.RequestException as e_media:
                error_detail = f"Error during Step 3 (Media Upload/Linking for Post {new_post_id}): {e_media}"
                if e_media.response is not None:
                    try: error_detail += f" | Status: {e_media.response.status_code} | API Response: {json.dumps(e_media.response.json())}"
                    except json.JSONDecodeError: error_detail += f" | Status: {e_media.response.status_code} | API Response Text: {e_media.response.text}"
                logging.error(error_detail)
            except Exception as e_general_media:
                error_msg = f"An unexpected error occurred during Step 3 (Media Upload/Linking for Post {new_post_id}): {e_general_media}"
                logging.exception(error_msg)
                # Continue, as the post itself was created.

    # Return success based on Step 1 (post creation)
    return {"success": True, "data": create_response_json} 