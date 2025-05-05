import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI # Changed import
# from langchain_google_genai import ChatGoogleGenerativeAI # Removed
from langchain_core.prompts import ChatPromptTemplate # Keep for message structure if needed, but not for chain
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import re # Import regex for better parsing
import sys # Import sys for exit
import json # Import json for JSON parsing
from datetime import datetime # Import datetime for timestamp
import requests # Added for WordPress interaction
import base64   # Added for WordPress interaction
import markdown # Import the markdown library
import mimetypes # Import mimetypes for determining image content type

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# --- LLM Client Initialization Function ---
def initialize_llm_clients():
    llm_blog = None
    llm_image_prompt = None
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    AVALAI_BASE_URL = "https://api.avalai.ir/v1"
    BLOG_MODEL_NAME = "gemini-2.5-pro-exp-03-25"
    IMAGE_PROMPT_MODEL_NAME = "gpt-4.1"
    TIMEOUT = 90

    if not GOOGLE_API_KEY:
        logging.warning("GOOGLE_API_KEY not found in environment variables. Cannot initialize LLM clients.")
        return None, None 
    
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

    except Exception as e:
        logging.exception(f"Error initializing ChatOpenAI clients: {e}")
        llm_blog = None 
        llm_image_prompt = None
    
    return llm_blog, llm_image_prompt

# --- WordPress Interaction Function ---
def create_draft_post(title: str, 
                      content: str, 
                      slug: str | None = None, 
                      tag_names: list[str] | None = None, # Accept tag names
                      primary_focus_keyword: str | None = None, # Add primary keyword
                      secondary_focus_keyword: str | None = None, # Add secondary keyword
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
    focus_keywords_to_send = None
    if primary_focus_keyword:
        focus_keywords_to_send = primary_focus_keyword
        if secondary_focus_keyword: # Append secondary if both exist
            focus_keywords_to_send += f",{secondary_focus_keyword}"
    elif secondary_focus_keyword: # Handle case where only secondary is provided
         focus_keywords_to_send = secondary_focus_keyword

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

# --- Main Blog Package Generation Function (Modified) ---
async def generate_persian_blog_package(
    llm_blog_client: ChatOpenAI,
    llm_image_prompt_client: ChatOpenAI,
    source_title: str,
    source_body: str,
    source_name: str,
    source_url: str
) -> dict:
    """ Docstring for generate_persian_blog_package """
    main_prompt = f"""
Objective: As an expert SEO Content Strategist specializing in engaging, humanized Persian content, generate a highly SEO-optimized blog post for my new website, hooshews.com, based on the provided article title and body. It's crucial this post has excellent SEO (aiming for a high Rank Math score) so people can find the site on Google. The post must be written entirely in humanized Persian, focusing strongly on SEO best practices for keyword selection (including LSI keywords), structure, metadata, and visual appeal, and conclude with source attribution.

Instructions:

Analyze: Thoroughly review the content of the provided article title and body below. Identify key concepts, arguments, target keywords, and potential LSI keywords.

--- START OF SOURCE TITLE --- 
{source_title}
--- END OF SOURCE TITLE ---

--- START OF SOURCE BODY ---
{source_body}
--- END OF SOURCE BODY ---

# Focus Keywords (Generate First)
Focus Keywords (کلمات کلیدی کانونی):

Generate **one primary focus keyword** and **one secondary focus keyword** in Persian based on the source title and body.
*   The **primary keyword** is the absolute most important term.
*   The **secondary keyword** is the next most important related term.
*   You can mix Persian and English terms within each keyword if it represents a common search phrase or technical concept (e.g., 'راهکارهای یادگیری AI').
These keywords will be used to optimize other elements.
Provide the primary keyword for the `primary_focus_keyword` key and the secondary for the `secondary_focus_keyword` key in the final JSON.

Title (عنوان):

*   Create a compelling and relevant title in Persian for the **main blog post heading (H1)**.
*   Incorporate the `primary_focus_keyword`.
*   Try to naturally incorporate the `secondary_focus_keyword` as well, if possible without sacrificing clarity or sounding forced.
*   Try to keep the meaning very close to the original source title, translating it appropriately into natural Persian.
*   **Handling English Terms:** Retain original English terms for technical concepts, brand names, specific jargon, or proper nouns where a direct Persian translation might lose meaning, search relevance, or accuracy. Alternatively, if you translate such a term to Persian, include the original English term in parentheses `()` immediately after the translation (e.g., `هوش مصنوعی (AI)`).
*   **Title Readability Enhancement:** 
    *   Attempt to use a **Power Word** (like "شگفت‌انگیز", "ضروری", "اثبات‌شده", "راز", "نهایی", "ساده") if it fits naturally and enhances clickability.
    *   Consider including a **number** (e.g., "7 راهکار...") if it makes sense for the content (like a list post).

# NEW: SEO Title (Rank Math)
SEO Title (عنوان سئو):

*   Generate a separate, concise title specifically optimized for **search engine results pages (SERPs)**.
*   **Strictly keep this title under 60 characters.**
*   **Crucially, include the exact `primary_focus_keyword` prominently, ideally near the beginning.**
*   Base it on the main Title and keywords, but prioritize brevity and SERP click-through rate.

Permalink/Slug (پیوندیکتا):

Generate a concise, SEO-friendly permalink (slug) based primarily on the `primary_focus_keyword` and source title.
Must be entirely in English. Use hyphens (-) to separate words.
Should accurately reflect the main topic and keywords.
Example: ai-learning-solutions

Meta Description (توضیح):

*   Write a compelling meta description in Persian (strictly between 150-160 characters).
*   **Crucially, include the exact `primary_focus_keyword` naturally within the description.**
*   Try to naturally incorporate the `secondary_focus_keyword` as well, if possible.
*   Accurately summarize the post's content to maximize click-through rate (CTR) from search results.
*   Include a strong call-to-action (e.g., "بیشتر بدانید") to improve CTR.

Content Generation:

*   **Introduction:** Start with a friendly, personal greeting addressing the Hooshews (هوشیوز) audience directly. Write the introduction (and the whole post) in a conversational, almost journal-like tone. Connect the topic to hooshews.com's focus on AI/tech news.
*   **Focus Keyword Placement:** 
    *   **Crucially, include the exact `primary_focus_keyword` within the first 10% of the main content body (after the intro).**
    *   **Incorporate both the `primary_focus_keyword` and `secondary_focus_keyword` naturally into `##` (H2) and `###` (H3) headings.**
    *   Maintain a **natural keyword density** for *both* focus keywords throughout the content, aiming for approximately 1-1.5% density *combined*, prioritizing the primary keyword slightly more. **Avoid keyword stuffing.**
*   **Body:** Write a comprehensive, *unique* Persian blog post that summarizes, explains, and potentially *adds value beyond* the key information from the source body. **Target a minimum word count of 600 words, aiming for longer comprehensive content where appropriate.** Ensure the content is unique and is not just a rehash or direct translation.
*   **Structure & Readability:** 
    *   Structure the content beautifully using Markdown. Make it visually appealing and easy to scan. Use Markdown elements like bullet points (`* point`), numbered lists (`1. point`), bold text (`**important term**`).
    *   Use appropriate Markdown for headings (e.g., `##` for H2 headings, `###` for H3 headings).
    *   **Crucially, keep paragraphs short and focused, ideally 2-4 sentences and well under 120 words each.**
    *   Add at least one unique insight or perspective (e.g., a practical tip, a local context, or a forward-looking question).
    *   **Suggest Media:** Where appropriate, insert placeholders like `[پیشنهاد تصویر: توضیح تصویر مورد نیاز در اینجا]` or `[پیشنهاد ویدیو: توضیح ویدیوی مورد نیاز در اینجا]` to guide manual media insertion later.
*   **Handling English Terms:** Within the body text, follow the same principle as for the title: keep essential English terms directly, or if translating, follow with the English term in parentheses `()` (e.g., `یادگیری ماشین (Machine Learning)`).
*   **Linking (External):** 
    *   **Goal:** Enhance credibility and provide value by linking externally to high-quality, authoritative sources.
    *   **What to Link:** Identify opportunities to link key **English terms, brand names (like OpenAI, Google Gemini), specific data points, technical concepts, or cited studies/sources** to their official/authoritative URLs.
    *   **Relevance & Value:** Only add links that genuinely enhance the reader's understanding or provide necessary attribution/evidence. Prioritize quality over quantity (a few good links are better than many weak ones).
    *   **Anchor Text:** Use **natural and descriptive anchor text** (the `[linked text]` part) that accurately reflects the content of the target URL. Avoid generic text like "click here".
    *   **URL Guessing:** Attempt to find the most relevant official or authoritative URL (e.g., link 'OpenAI' to `https://openai.com/`).
    *   **Format:** Embed these links **directly** within the content body using standard Markdown syntax: `[طبیعی و توصیفی لنگر متن](URL)`. Ensure the URL is valid.
    *   **Selectivity:** Be professional and selective; do not over-link.
    *   *Internal linking will be handled manually.* 
*   **Language & Conclusion:**
    *   Use Persian numerals (e.g., ۱, ۲, ۳) for any numbers within the Persian text.
    *   Conclude the main body of the article with a Markdown horizontal rule (`---`) on its own line, followed immediately by the source attribution text formatted exactly as: `منبع: [{source_name}]({source_url})` using the provided source name and URL.

Language and Tone:

Language: Entirely in Persian (Farsi) (except for the پیوندیکتا and specific English terms as instructed above). Use Persian numerals (۱, ۲, ۳...).
Style: Natural, humanized, friendly, and engaging. Avoid overly formal or robotic language. Write conversationally, as if explaining to a friend (like a journal entry). Make it accessible.

Thumbnail Image:

*   Alt Text (متن جایگزین): Provide descriptive Persian alt text for the thumbnail image. **Crucially, include the exact `primary_focus_keyword` naturally within the alt text.** Try to include the `secondary_focus_keyword` as well if natural. Incorporate other relevant keywords (from the source title and body) for image SEO.
*   Filename: The English `slug` generated will be used to create the filename `hooshews.com-[slug].webp` later.

Tags:

# MODIFIED: Ask for specific English AND general Persian tags
Suggest a total of **up to 7 tags** based on the source title and body, chosen for SEO value and relevance:
*   **3 English Tags:** Focus on **specific entities, technical terms, or proper nouns** (e.g., "Google Gemini", "OpenAI", "LLM", "API"). Avoid general conceptual English tags.
*   **4 Persian Tags:** Focus on **general but highly relevant SEO keywords** related to the topic (e.g., "هوش مصنوعی", "امنیت آنلاین", "گوگل", "فناوری").

Instagram Story Teaser (for Traffic Generation):

Generate two pieces of text optimized for an Instagram Story slide, designed to maximize curiosity and drive traffic to the full blog post on hooshews.com.
*   **Goal:** Create an irresistible hook that makes users *immediately* want to swipe up or visit the link in bio. The text must be extremely concise and visually scannable on a Story background.
*   **Content Focus:** Condense the main blog post's description (or the core concept it represents) into a very short summary that highlights the key topic and its significance or impact. This summary should provide enough information to pique interest but still require a visit to the website for the full explanation.
*   **Handling English Terms:** Apply the same guidelines for handling English technical terms, brand names, or specific jargon (keeping them directly in English like `API`, `GPT-4`, or adding English in parentheses after a Persian translation like `هوش مصنوعی (AI)`) as outlined for the main article title and body.
*   **Tone:** Energetic, attention-grabbing, conversational, and direct. Use urgency or curiosity triggers.
*   **Emoji Use:** Suggest incorporating 1-2 relevant and visually engaging emojis (like ✨, 🚀, 🤔, 💡, 🔥, etc.) within the description to enhance appeal, but only if natural.

Output Format & Style:

Provide the entire output strictly as a **single JSON object**. Do **NOT** include any text before or after the JSON object. Do **NOT** use markdown code fences (```json ... ```). The JSON object should have the following keys:

*   `"primary_focus_keyword"`: [Generated single Persian Primary Focus Keyword String]
*   `"secondary_focus_keyword"`: [Generated single Persian Secondary Focus Keyword String]
*   `"title"`: [Generated Persian Title String for H1, optimized as per instructions]
*   `"seo_title"`: [Generated Persian SEO Title String for Rank Math (<60 chars), optimized as per instructions]
*   `"slug"`: [Generated English Slug String]
*   `"meta_description"`: [Generated Persian Meta Description String (150-160 chars), optimized as per instructions]
*   `"alt_text"`: [Generated Persian Alt Text String, optimized as per instructions]
*   `"tags"`: [Array of **up to 7** Tag Strings (containing the 3 specific English and 4 general Persian tags suggested)]
*   `"content"`: [Generated Persian Blog Post Content as a single Markdown string, optimized for structure, keywords, readability, and including media suggestions, external links, and source attribution as per instructions]
*   `"instagram_story_title"`: [Generated extremely concise Persian Story Title String]
*   `"instagram_story_description"`: [Generated very short Persian Story Teaser String]

Ensure all string values in the JSON are properly escaped if necessary.


---
"""
    messages = [HumanMessage(content=main_prompt)]
    blog_package = {}
    blog_llm_raw_output = None
    image_prompt_output = None
    processed_output = None # Initialize here

    try:
        logging.info(f"Invoking ChatOpenAI (Blog) (async) for Persian blog generation (Source: {source_name}, Title: {source_title[:50]}...).)")
        response = await llm_blog_client.ainvoke(messages) # Make sure response is assigned
        blog_llm_raw_output = response.content 
        logging.info("ChatOpenAI (Blog) invocation successful (async).")

        processed_output = blog_llm_raw_output.strip() # Assign here
        if processed_output.startswith("```json"):
            processed_output = processed_output[7:]
        if processed_output.endswith("```"):
            processed_output = processed_output[:-3]
        processed_output = processed_output.strip()

        try:
            blog_package = json.loads(processed_output)
            logging.info("Successfully parsed JSON response from Blog LLM.")
            # Updated required_keys to match the new output format section
            required_keys = ["primary_focus_keyword", "secondary_focus_keyword", "title", "seo_title", "slug", "meta_description", "alt_text", "tags", "content", "instagram_story_title", "instagram_story_description"]
            if not all(key in blog_package for key in required_keys):
                # Calculate missing keys properly
                present_keys = set(blog_package.keys())
                required_keys_set = set(required_keys)
                missing_keys = list(required_keys_set - present_keys)
                logging.error(f"Missing required keys in parsed JSON: {missing_keys}") 
                save_output_to_file(raw_blog_output=processed_output, error="Missing required keys", slug='json-error')
                return {"error": "LLM response did not contain all required fields in JSON."}
            
            slug = blog_package.get('slug')
            if slug:
                blog_package['filename'] = f"hooshews.com-{slug}.webp"
            else:
                blog_package['filename'] = "hooshews.com-missing-slug.webp"
                logging.warning("Slug key missing or empty in JSON, using default filename.")

        except json.JSONDecodeError as json_err:
            logging.error(f"Failed to decode JSON from LLM response: {json_err}")
            logging.error(f"Raw response text: {processed_output}")
            save_output_to_file(raw_blog_output=processed_output, error=str(json_err), slug='json-decode-error') # Use processed_output here
            return {"error": f"Could not parse the AI's response as valid JSON. See logs."}
        
        if llm_image_prompt_client:
            if source_title and source_body: 
                 image_prompt_output = await generate_image_prompt(
                    llm_client=llm_image_prompt_client,
                    header=source_title,
                    description=source_body
                )
                 blog_package['image_prompt'] = image_prompt_output
            else:
                 blog_package['image_prompt'] = "Error: Could not generate image prompt due to missing original source title or body."
                 logging.warning("Missing source_title or source_body for image prompt generation.")
        else:
            blog_package['image_prompt'] = "Error: Image prompt generation skipped because the required LLM client was not available."
            logging.error("Skipping image prompt generation; llm_image_prompt_client argument was None.")

        save_output_to_file(
            raw_blog_output=processed_output,
            raw_image_prompt=image_prompt_output,
            parsed_package=blog_package,
            slug=blog_package.get('slug', 'no-slug')
        )
        return blog_package

    except Exception as e:
        logging.exception(f"Error during async ChatOpenAI invocation for blog generation: {e}")
        # Use processed_output here as well, which might be None if error happened early
        save_output_to_file(raw_blog_output=processed_output, error=str(e), slug='error') 
        return {"error": f"Sorry, I encountered an error generating the blog post: {e}"}

# Placeholder function remains the same
def extract_keywords(text):
    # ... (keep existing function body)
    logging.info(f"Keyword extraction requested for: {text[:50]}...")
    return ["keyword1", "keyword2"]

# --- Image Prompt Generation Function ---
async def generate_image_prompt(llm_client: ChatOpenAI, header: str, description: str) -> str:
    """ Docstring for generate_image_prompt """
    prompt_fstring = f"""
You are a Visual Concept AI, specializing in crafting unique and compelling image prompts for AI news thumbnails. Your goal is to generate a *single*, *novel*, *high-quality*, and *effective* prompt for an **image thumbnail** suitable for an AI startup news article or blog post (`hooshews.com`), incorporating a subtle signature character and optimizing for clickability.

Each time, I will give you:
1.  **`[HEADER]`**: The main title or headline of the article/post.
2.  **`[DESCRIPTION]`**: A brief explanation or context for the header.

Based on these inputs, craft **one** creative and well-structured image prompt. This prompt **must** adhere to the following structure and requirements:

1.  Start exactly with the phrase: `Create image for a blog post thumbnail.`
2.  Clearly instruct the image generator to create a visually engaging, professional thumbnail that primarily conveys the core theme of the `[HEADER]` and `[DESCRIPTION]`, drawing inspiration from keywords within the inputs. The scene should feel relevant to the AI industry or startup scene.
3.  **Visual Style:** Incorporate a description of the desired visual style (e.g., photorealistic with modern elements, minimalist illustration with bold colors, abstract tech theme, vibrant vector art, cinematic). Choose a style that is engaging for news thumbnails.
4.  **Subtle Character Integration:** Crucially, include instructions for the image generator to incorporate the visual likeness of a specific character photo/avatar (which I will provide when using the generated prompt). This integration must be **subtle and creative**:
    *   Use the character's distinct visual appearance (face, clothing style if relevant) as the reference.
    *   **Do NOT rigidly copy the exact pose, gesture, or background** from the provided character photo.
    *   **Adapt the character's posture, position, scale, and action** so they fit *naturally and contextually* within the generated scene's narrative or environment.
    *   The character should **not** be the main focus but should exist *within* the scene almost like an easter egg or a recurring signature, hinting at a consistent presence. The placement should feel intentional but discreet.
5.  **Subtle Branding:** Include a subtle reference to "Hooshews" or incorporate the brand color `#4379f2` naturally within the scene (e.g., as an accent color on an object, a subtle logo on a device screen, a background element). Keep it discreet and not distracting.
6.  **Relevance to Content:** Ensure the thumbnail visually reflects the main theme or keywords of the blog post ([HEADER], [DESCRIPTION]). 
7.  Ensure the final prompt you generate is clear, evocative, and likely to produce a compelling, unique, and high-CTR (Click-Through Rate) thumbnail image fulfilling all these conditions.

**Provide only the generated image prompt itself as your response.**

---

**`[HEADER]`**: {header}
**`[DESCRIPTION]`**: {description}
---
    """
    messages = [HumanMessage(content=prompt_fstring)]
    try:
        logging.info(f"Invoking Image Prompt LLM (async)...")
        response = await llm_client.ainvoke(messages) # Ensure response is assigned here
        logging.info("Image Prompt LLM invocation successful (async).")
        return response.content.strip()
    except Exception as e:
        logging.exception(f"Error during async Image Prompt LLM invocation: {e}")
        return f"Error generating image prompt: {e}"

# --- Helper function to save output --- 
def save_output_to_file(raw_blog_output=None, raw_image_prompt=None, parsed_package=None, error=None, slug='output'):
    """ Docstring for save_output_to_file """
    try:
        output_dir = "answers"
        counter_file = os.path.join(output_dir, "counter.txt")
        os.makedirs(output_dir, exist_ok=True)
        count = 0
        try:
            with open(counter_file, 'r') as f_count:
                count = int(f_count.read().strip())
        except FileNotFoundError:
            logging.info("Counter file not found, starting count at 0.")
            count = 0
        except ValueError:
            logging.warning(f"Invalid content in {counter_file}. Resetting count to 0.")
            count = 0
        except Exception as e_read:
             logging.error(f"Error reading counter file {counter_file}: {e_read}. Resetting count.")
             count = 0
        next_count = count + 1
        try:
            with open(counter_file, 'w') as f_count:
                f_count.write(str(next_count))
        except Exception as e_write:
            logging.error(f"Failed to write next count ({next_count}) to {counter_file}: {e_write}. Filename might reuse count.")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_slug = re.sub(r'[^\w-]+', '', slug)[:50]
        # Ensure filename is defined before logging
        filename = os.path.join(output_dir, f"{next_count:04d}_{safe_slug}_{timestamp}.json")

        data_to_save = {
            "id": next_count,
            "timestamp": timestamp,
            "status": "error" if error else "success",
            "error_message": error,
            "raw_blog_llm_output": raw_blog_output,
            "raw_image_prompt_llm_output": raw_image_prompt,
            "final_parsed_package": parsed_package,
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        
        # Now filename is guaranteed to be defined here
        logging.info(f"Successfully saved output to {filename}") 
    except Exception as save_e:
        logging.exception(f"Failed to save output to file: {save_e}")
 