import streamlit as st
import sys
import os
import asyncio
from PIL import Image
import io
import logging
import json

from .content_generator import generate_persian_blog_package, generate_instagram_post_texts, analyze_blog_for_instagram_inputs, generate_instagram_story_teasers
from .llm_clients import initialize_llm_clients
from .wordpress_handler import create_draft_post
from .file_utils import list_pantry_baskets_async, get_pantry_basket_content_async

GRAPHIC_DIR = "images"

def main():
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("GOOGLE_API_KEY not found in environment variables. Cannot attempt to initialize LLMs.")
        st.stop()

    st.set_page_config(page_title="Hooshews Persian Blog Generator", layout="wide")
    st.title("📝 Hooshews Persian Blog Post Generator")
    st.caption("Generate SEO-optimized Persian blog posts from English source articles.")

    # Initialize all three LLM clients
    llm_blog, llm_image_prompt, llm_instagram_text = initialize_llm_clients()

    st.header("Source Article Input")
    source_title = st.text_input("Source Title (H1)")
    source_body = st.text_area("Paste Source English Article Body Here", height=400)
    source_name = st.text_input("Source Name (e.g., Engadget, TechCrunch)")
    source_url = st.text_input("Source URL (the exact link to the source article)")

    st.divider()
    st.header("Or Upload Existing JSON Output")
    uploaded_json_file = st.file_uploader("Upload a previously generated .json file from the 'answers' folder", type=["json"])

    if uploaded_json_file is not None:
        try:
            string_data = uploaded_json_file.getvalue().decode("utf-8")
            uploaded_full_data = json.loads(string_data)
            
            if 'final_parsed_package' in uploaded_full_data and uploaded_full_data['final_parsed_package'] is not None:
                st.session_state.uploaded_data = uploaded_full_data['final_parsed_package']
                st.session_state.generation_result = None # Clear any previous generation to prioritize upload
                st.success(f"Successfully loaded data from local file: {uploaded_json_file.name}")
            else:
                st.error(f"Error: 'final_parsed_package' key not found or is null in {uploaded_json_file.name}. Cannot load data.")
                if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data 

        except json.JSONDecodeError:
            st.error(f"Error: Could not decode JSON from {uploaded_json_file.name}. Please ensure it's a valid JSON file.")
            if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data 
        except Exception as e:
            st.error(f"An error occurred while processing the uploaded file: {e}")
            if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data 
    
    # --- Pantry Cloud Loading Section ---
    st.subheader("Load from Pantry Cloud")
    pantry_id_env = os.getenv("PANTRY_ID")

    if not pantry_id_env:
        st.warning("PANTRY_ID not found in environment variables. Pantry loading is disabled.")
    else:
        if "pantry_basket_names" not in st.session_state:
            st.session_state.pantry_basket_names = []

        if st.button("Fetch Baskets from Pantry"):
            with st.spinner("Fetching basket list from Pantry..."):
                baskets = asyncio.run(list_pantry_baskets_async(pantry_id_env))
                if baskets is not None:
                    st.session_state.pantry_basket_names = baskets
                    if not baskets:
                        st.info("No baskets found in your Pantry.")
                    else:
                        st.success(f"Found {len(baskets)} baskets in your Pantry.")
                else:
                    st.error("Failed to fetch basket list from Pantry. Check logs for details.")
                    st.session_state.pantry_basket_names = []
        
        if st.session_state.pantry_basket_names:
            selected_pantry_basket = st.selectbox(
                "Select a Pantry basket to load:",
                options=st.session_state.pantry_basket_names
            )

            if st.button("Load Selected Pantry Basket"):
                if selected_pantry_basket:
                    with st.spinner(f"Loading '{selected_pantry_basket}' from Pantry..."):
                        basket_content = asyncio.run(get_pantry_basket_content_async(pantry_id_env, selected_pantry_basket))
                        if basket_content and isinstance(basket_content, dict):
                            if 'final_parsed_package' in basket_content and basket_content['final_parsed_package'] is not None:
                                st.session_state.uploaded_data = basket_content['final_parsed_package']
                                st.session_state.generation_result = None # Clear any previous generation
                                st.success(f"Successfully loaded data from Pantry basket: {selected_pantry_basket}")
                            else:
                                st.error(f"Error: 'final_parsed_package' key not found or is null in Pantry basket '{selected_pantry_basket}'.")
                                if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data
                        else:
                            st.error(f"Failed to load or parse content from Pantry basket '{selected_pantry_basket}'. Check logs.")
                            if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data
                else:
                    st.warning("No Pantry basket selected.")
        elif not st.session_state.pantry_basket_names and pantry_id_env: # Only show if pantry ID exists but no baskets fetched/found
            st.caption("Click 'Fetch Baskets from Pantry' to see available saves.")

    st.divider()

    # Check if all LLM clients are initialized
    if llm_blog and llm_image_prompt and llm_instagram_text:
        if "generation_result" not in st.session_state:
            st.session_state.generation_result = None

        # Add checkboxes for optional generations
        include_instagram_posts = st.checkbox("Include Instagram Post Texts", value=True, help="Generate viral title and caption for Instagram based on the blog content.")
        include_story_teasers = st.checkbox("Include Instagram Story Teasers", value=True, help="Generate Farsi teaser snippets for Instagram Stories.")
        include_iranian_video_prompt = st.checkbox("Include Iranian Farsi Video Prompt", value=False, help="Generate a short video prompt with Iranian context and Farsi dialogue.")

        if st.button("✨ Generate Persian Blog Post Package"):
            if not source_name or not source_title or not source_body or not source_url:
                st.warning("Please provide Source Name, Source Title, Source Body, and Source URL.")
            else:
                with st.spinner("Generating Persian blog post, image prompts (artistic & realistic blog + Instagram), video prompts, and Instagram texts..."): # Updated spinner
                    result_package = asyncio.run(generate_persian_blog_package(
                        llm_blog_client=llm_blog, 
                        llm_image_prompt_client=llm_image_prompt, 
                        llm_instagram_text_client=llm_instagram_text, # Pass the Instagram text client
                        source_title=source_title, 
                        source_body=source_body,   
                        source_name=source_name,
                        source_url=source_url,
                        include_instagram_texts=include_instagram_posts, # Pass the checkbox state for post
                        include_story_teasers=include_story_teasers, # Pass the checkbox state for story
                        include_iranian_video_prompt=include_iranian_video_prompt # NEW: Pass the checkbox state
                    ))
                st.session_state.generation_result = result_package 
                if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data # Clear uploaded data if new generation occurs
        
        display_data = None
        data_source_message = ""
        if 'uploaded_data' in st.session_state and st.session_state.uploaded_data is not None:
            display_data = st.session_state.uploaded_data
            data_source_message = "Displaying data from uploaded file."
        elif 'generation_result' in st.session_state and st.session_state.generation_result is not None:
            display_data = st.session_state.generation_result
            data_source_message = "Displaying newly generated data."

        if display_data:
            st.info(data_source_message)
            result_package = display_data # This is the 'final_package' from utils
            st.header("Generated Output")
            st.markdown('<div dir="rtl">', unsafe_allow_html=True)

            if result_package.get("error"):
                st.error(result_package["error"])
            else:
                # Display Metadata, Content, Links, Image Prompt, Instagram, Image Uploader
                with st.expander("📋 Metadata", expanded=True):
                    st.markdown(f"**عنوان اصلی (H1):** {result_package.get('title', 'N/A')}")
                    st.markdown(f"**عنوان سئو (Rank Math):**")
                    st.code(result_package.get('seo_title', 'N/A'), language=None)
                    st.markdown("**پیوندیکتا (Slug):**")
                    st.code(result_package.get('slug', 'N/A'), language=None)
                    st.markdown(f"**توضیح (Meta Description):**")
                    st.code(result_package.get('meta_description', 'N/A'), language=None)
                    st.markdown(f"**متن جایگزین تصویر بندانگشتی (Alt Text):**")
                    st.code(result_package.get('alt_text', 'N/A'), language=None)
                    st.markdown(f"**نام فایل تصویر بندانگشتی:**")
                    st.code(result_package.get('filename', 'N/A'), language=None)
                    st.markdown(f"**تگ‌ها:**")
                    tags_list = result_package.get('tags', ['N/A'])
                    tags_string = ', '.join(tags_list)
                    st.code(tags_string, language=None)
                    st.markdown(f"**کلمه کلیدی کانونی:**")
                    primary_kw = result_package.get('primary_focus_keyword', 'N/A')
                    secondary_kw = result_package.get('secondary_focus_keyword')
                    additional_kws = result_package.get('additional_focus_keywords') 
                    
                    focus_kw_list = [primary_kw] if primary_kw != 'N/A' else []
                    if secondary_kw:
                        focus_kw_list.append(secondary_kw)
                    if additional_kws and isinstance(additional_kws, list):
                         focus_kw_list.extend(additional_kws)
                    
                    focus_kw_display = ", ".join(focus_kw_list)
                    st.code(focus_kw_display if focus_kw_display else 'N/A', language=None)
                
                st.divider()
                with st.expander("📄 محتوای اصلی وبلاگ (Markdown Rendered)", expanded=True):
                    st.markdown(result_package.get('content', 'N/A'))
                    st.markdown("**برای کپی کردن:**")
                    st.code(result_package.get('content', 'N/A'), language='markdown')
                st.divider()
                with st.expander("🖼️ پرامپت تولید تصویر (وبلاگ - هنری)"):
                    st.code(result_package.get('image_prompt', 'N/A'), language=None)
                st.divider()
                with st.expander("📸 پرامپت تولید تصویر (وبلاگ - واقع‌گرایانه)"):
                    st.code(result_package.get('realistic_image_prompt', 'N/A'), language=None)
                st.divider()
                # This section now directly uses data from result_package (which is display_data)
                with st.expander("📸 اینستاگرام: عنوان، کپشن، پرامپت تصویر و ویدیو", expanded=True):
                    st.markdown("### Instagram Content Generation Components")
                    st.markdown("""
This section contains all components needed for creating engaging Instagram content:
1. Post Title & Caption - The text content for your Instagram post
2. Image Prompt - Instructions for generating your post's image (either static or video-ready)
3. Video Prompt - Instructions for transforming the generated image into a dynamic video
                    """)
                    st.divider()
                    
                    st.markdown("**عنوان ویروسی پست اینستاگرام:**")
                    st.text_input("", value=result_package.get('instagram_post_title', 'N/A'), disabled=True, key="insta_title_disp")
                    st.markdown("**کپشن کامل پست اینستاگرام:**")
                    st.text_area("", value=result_package.get('instagram_post_caption', 'N/A'), height=250, disabled=True, key="insta_caption_disp")
                    
                    st.divider()
                    st.markdown("### Image Generation")
                    st.markdown("**پرامپت تصویر اینستاگرام (عکس ثابت):**")
                    st.text_area("", value=result_package.get('instagram_static_image_prompt', 'N/A'), height=150, disabled=True, key="insta_static_img_prompt_disp")
                    st.info("📸 **Image Type: Static Image Prompt** - Optimized for single-frame visual impact. Focuses on strong composition and focal points. Perfect for static posts. Emphasizes immediate visual appeal. Designed for maximum engagement without motion.")
                    
                    st.markdown("**پرامپت تصویر اینستاگرام (آماده برای ویدیو):**")
                    st.text_area("", value=result_package.get('instagram_video_ready_image_prompt', 'N/A'), height=150, disabled=True, key="insta_video_ready_img_prompt_disp")
                    st.info("📹 **Image Type: Video-Ready Image Prompt** - Optimized for animation with separable layers. Includes elements designed for movement. Perfect for video transformation. Contains depth and parallax-ready components. Includes atmospheric elements for animation.")
                    
                    st.divider()
                    st.markdown("### Video Generation")
                    st.markdown("**پرامپت ویدیو اینستاگرام (برای تولید ویدیو از عکس):**")
                    st.text_area("", value=result_package.get('instagram_video_prompt', 'N/A'), height=200, disabled=True, key="insta_video_prompt_disp")
                    
                    if result_package.get('instagram_video_prompt', 'N/A') != 'N/A' and 'not generated' not in result_package.get('instagram_video_prompt', ''):
                        st.info("""
🎬 **How to Create Your Instagram Video:**

1. First, use the **Image Prompt** above with your preferred AI image generation tool (like Midjourney or DALL-E) to create your base image.

2. Then, use this **Video Prompt** with video generation tools like:
   - Google Veo 2
   - RunwayML
   - D-ID
   - or similar AI video generators

3. The prompt is specifically designed following Veo 2 best practices to create:
   - Engaging movement
   - Professional transitions
   - Seamless loops
   - Viral-worthy animations

4. The resulting video will be perfect for Instagram posts, maintaining the professional and satirical tech culture vibe while adding captivating motion.
                        """)
                    elif 'disabled by user' in result_package.get('instagram_video_prompt', ''):
                        st.info("ℹ️ Video prompt generation is currently disabled. Enable Instagram text generation to get video prompts.")
                    else:
                        st.warning("⚠️ Video prompt generation encountered an error. You can still use the static image prompt above for your post.")
                st.divider()
                st.success("Text generation complete!")
                st.divider()

                # NEW: Display Iranian Farsi Video Prompt if generated
                with st.expander("🎥 پرامپت ویدئو فارسی-ایرانی (مستقل)", expanded=True):
                    iranian_video_prompt = result_package.get('iranian_farsi_video_prompt')
                    if iranian_video_prompt and not iranian_video_prompt.startswith("Error"):
                        st.markdown("**پرامپت نهایی برای تولید ویدئو:**")
                        st.code(iranian_video_prompt, language=None)
                        st.info("این پرامپت برای تولید ویدئوهای کوتاه با فضای ایرانی و دیالوگ فارسی، مستقل از عکس اینستاگرام است.")
                    elif iranian_video_prompt and iranian_video_prompt.startswith("Error"):
                        st.error(f"Error generating Iranian Farsi video prompt: {iranian_video_prompt}")
                    else:
                        st.info("پرامپت ویدئوی فارسی-ایرانی تولید نشد. (تیک مربوطه را فعال کنید یا خطا رخ داده است.)")

                # Display Instagram Story Teasers if generated
                with st.expander("📸 اینستاگرام: استوری تیزرها", expanded=True):
                    story_teasers = result_package.get('instagram_story_teasers')
                    if story_teasers and isinstance(story_teasers, dict) and not story_teasers.get("error"):
                        st.markdown(f"**1. Main Title (تیتر اصلی):** {story_teasers.get('story_main_title', 'N/A')}")
                        st.markdown(f"**2. Subtitle/Question (زیرنویس/سوال):** {story_teasers.get('story_subtitle', 'N/A')}")
                        st.markdown(f"**3. Body Text (متن بدنه):**")
                        st.text_area("Story Body Text", value=story_teasers.get('story_body_text', 'N/A'), height=150, disabled=True, key="story_body_disp")
                    elif story_teasers and story_teasers.get("error"):
                         st.error(f"Error generating story teasers: {story_teasers.get('error')}")
                         if story_teasers.get("raw_output"):
                             st.code(story_teasers.get("raw_output"), language=None)
                    else:
                        st.info("Instagram Story teasers not generated or not requested.")
                        st.markdown("**1. Main Title (تیتر اصلی):** N/A")
                        st.markdown("**2. Subtitle/Question (زیرنویس/سوال):** N/A")
                        st.markdown("**3. Body Text (متن بدنه):** N/A")

                st.divider()
                st.subheader("🖼️ Upload and Save Thumbnail Images")
                
                # Artistic Thumbnail Upload
                st.markdown("**🎨 Artistic Thumbnail (Blog):**")
                uploaded_image = st.file_uploader("Choose an artistic image file (JPG, PNG, etc.)...", type=["jpg", "jpeg", "png"], key="artistic_upload")
                
                if uploaded_image is not None:
                    target_filename = result_package.get('filename')
                    if target_filename:
                        try:
                            save_path = os.path.join(GRAPHIC_DIR, target_filename)
                            os.makedirs(GRAPHIC_DIR, exist_ok=True)
                            img = Image.open(uploaded_image)
                            st.image(img, caption="Uploaded Artistic Image", use_column_width=True)
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                                logging.info(f"Converted image mode from {img.mode} to RGB.")
                            logging.info(f"Attempting to save artistic image to: {save_path}")
                            img.save(save_path, 'WEBP')
                            st.success(f"Artistic image successfully saved as WebP to: {save_path}")
                        except Exception as img_e:
                            st.error(f"Error processing or saving artistic image: {img_e}")
                            logging.exception(f"Error processing/saving uploaded artistic image:")
                    else:
                        st.error("Could not determine the target filename from the generated results.")
                
                # Realistic Thumbnail Upload
                st.markdown("**📸 Realistic Thumbnail (Blog):**")
                # Create realistic filename by adding "_realistic" before the extension
                realistic_filename = None
                if result_package.get('filename'):
                    base_name = result_package.get('filename').replace('.webp', '')
                    realistic_filename = f"{base_name}_realistic.webp"
                
                uploaded_realistic_image = st.file_uploader("Choose a realistic image file (JPG, PNG, etc.)...", type=["jpg", "jpeg", "png"], key="realistic_upload")
                
                if uploaded_realistic_image is not None:
                    if realistic_filename:
                        try:
                            save_path = os.path.join(GRAPHIC_DIR, realistic_filename)
                            os.makedirs(GRAPHIC_DIR, exist_ok=True)
                            img = Image.open(uploaded_realistic_image)
                            st.image(img, caption="Uploaded Realistic Image", use_column_width=True)
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                                logging.info(f"Converted realistic image mode from {img.mode} to RGB.")
                            logging.info(f"Attempting to save realistic image to: {save_path}")
                            img.save(save_path, 'WEBP')
                            st.success(f"Realistic image successfully saved as WebP to: {save_path}")
                        except Exception as img_e:
                            st.error(f"Error processing or saving realistic image: {img_e}")
                            logging.exception(f"Error processing/saving uploaded realistic image:")
                    else:
                        st.error("Could not determine the realistic filename from the generated results.")

            st.markdown('</div>', unsafe_allow_html=True)

            st.divider()
            st.subheader("🚀 Send to WordPress")
            if st.button("Create Draft Post in WordPress"):
                wp_title = display_data.get('title')
                wp_content = display_data.get('content')
                wp_slug = display_data.get('slug') 
                wp_tag_names = display_data.get('tags') # Get tag names from LLM output
                wp_primary_focus_keyword = display_data.get('primary_focus_keyword') # Get primary focus keyword
                wp_secondary_focus_keyword = display_data.get('secondary_focus_keyword') # Get secondary focus keyword
                wp_additional_focus_keywords = display_data.get('additional_focus_keywords') # Get additional keywords
                # Get SEO Title and Description from LLM output
                wp_seo_title = display_data.get('seo_title') # Use generated SEO title
                wp_seo_description = display_data.get('meta_description') # Use generated meta description
                wp_image_filename = display_data.get('filename') # Get expected image filename
                wp_image_alt_text = display_data.get('alt_text') # Get image alt text
                
                # Check if images exist (prioritize realistic over artistic)
                wp_image_path = None
                if wp_image_filename:
                    # First check for realistic image
                    base_name = wp_image_filename.replace('.webp', '')
                    realistic_image_path = os.path.join(GRAPHIC_DIR, f"{base_name}_realistic.webp")
                    artistic_image_path = os.path.join(GRAPHIC_DIR, wp_image_filename)
                    
                    if os.path.exists(realistic_image_path):
                        wp_image_path = realistic_image_path
                        st.info(f"Found realistic image: {realistic_image_path}")
                    elif os.path.exists(artistic_image_path):
                        wp_image_path = artistic_image_path
                        st.info(f"Found artistic image: {artistic_image_path}")
                    else:
                        st.warning(f"Image files not found at expected paths: {realistic_image_path} or {artistic_image_path}. Please place an image there. The post will be created without a featured image.")
                        wp_image_alt_text = None # Don't pass alt text if image isn't there
                else:
                    st.warning("Filename for image not found in generated data. Cannot check for image.")
                    wp_image_alt_text = None

                # Removed Test values for SEO meta 
                # Removed Test values for Category and Tag IDs

                if wp_title and wp_content:
                    with st.spinner("Sending draft to WordPress (Step 1: Create Post, Step 2: Update Rank Math, Step 3: Upload Image if found)..."):
                        # Call updated function: Pass image path and alt text (or None)
                        wp_result = create_draft_post(title=wp_title, 
                                                    content=wp_content, 
                                                    slug=wp_slug,
                                                    tag_names=wp_tag_names, # Pass the list of names
                                                    primary_focus_keyword=wp_primary_focus_keyword, # Pass primary
                                                    secondary_focus_keyword=wp_secondary_focus_keyword, # Pass secondary
                                                    additional_focus_keywords=wp_additional_focus_keywords, # Pass additional
                                                    seo_title=wp_seo_title, # Pass SEO Title
                                                    seo_description=wp_seo_description, # Pass SEO Description
                                                    image_path=wp_image_path, # Pass found image path or None
                                                    image_alt_text=wp_image_alt_text # Pass alt text or None
                                                    )
                    
                    if wp_result.get("success"):
                        st.success("✅ Successfully created draft post! Check WordPress for Category 26, tags, and Rank Math fields (via custom endpoint).")
                        wp_data = wp_result.get("data", {})
                        draft_id = wp_data.get('id')
                        draft_link = wp_data.get('link')
                        if draft_id and draft_link:
                            preview_link = f"{draft_link}?preview=true"
                            edit_link = draft_link.replace("?p=", "post.php?post=").replace("&preview=true", "&action=edit")
                            st.markdown(f"**Draft ID:** {draft_id}")
                            st.markdown(f"**Preview Draft Link:** [{preview_link}]({preview_link})")
                            st.markdown(f"**Attempted Edit Link:** [{edit_link}]({edit_link})")
                        else:
                            st.info("Could not retrieve draft ID or link from WordPress response.")
                    else:
                        st.error(f"❌ Failed to create WordPress draft (Step 1 failed): {wp_result.get('error')}")
                else:
                    st.warning("Cannot create draft. Title or Content missing from the generated/loaded data.")

    else:
        st.error("LLM clients could not be initialized. Please check your GOOGLE_API_KEY and network connection.")

if __name__ == "__main__":
    main()