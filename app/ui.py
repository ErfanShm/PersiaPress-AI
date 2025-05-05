import streamlit as st
import sys
import os
import asyncio
from PIL import Image
import io
import logging
import json

from .utils import generate_persian_blog_package, initialize_llm_clients, create_draft_post

GRAPHIC_DIR = "images"

def main():
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("GOOGLE_API_KEY not found in environment variables. Cannot attempt to initialize LLMs.")
        st.stop()

    st.set_page_config(page_title="Hooshews Persian Blog Generator", layout="wide")
    st.title("📝 Hooshews Persian Blog Post Generator")
    st.caption("Generate SEO-optimized Persian blog posts from English source articles.")

    llm_blog, llm_image_prompt = initialize_llm_clients()

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
                st.session_state.generation_result = None
                st.info(f"Successfully loaded data from: {uploaded_json_file.name}")
            else:
                st.error(f"Error: 'final_parsed_package' key not found or is null in {uploaded_json_file.name}. Cannot load data.")
                if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data 

        except json.JSONDecodeError:
            st.error(f"Error: Could not decode JSON from {uploaded_json_file.name}. Please ensure it's a valid JSON file.")
            if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data 
        except Exception as e:
            st.error(f"An error occurred while processing the uploaded file: {e}")
            if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data 
    st.divider()

    if llm_blog and llm_image_prompt:
        if "generation_result" not in st.session_state:
            st.session_state.generation_result = None

        if st.button("✨ Generate Persian Blog Post Package"):
            if not source_name or not source_title or not source_body or not source_url:
                st.warning("Please provide Source Name, Source Title, Source Body, and Source URL.")
            else:
                with st.spinner("Generating Persian blog post and image prompt..."):
                    result_package = asyncio.run(generate_persian_blog_package(
                        llm_blog_client=llm_blog, 
                        llm_image_prompt_client=llm_image_prompt, 
                        source_title=source_title, 
                        source_body=source_body,   
                        source_name=source_name,
                        source_url=source_url
                    ))
                st.session_state.generation_result = result_package 
                if 'uploaded_data' in st.session_state: del st.session_state.uploaded_data 
        
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
            result_package = display_data
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
                    focus_kw_display = primary_kw
                    if secondary_kw:
                        focus_kw_display += f", {secondary_kw}"
                    st.code(focus_kw_display, language=None)
                
                st.divider()
                with st.expander("📄 محتوای اصلی وبلاگ (Markdown Rendered)", expanded=True):
                    st.markdown(result_package.get('content', 'N/A'))
                    st.markdown("**برای کپی کردن:**")
                    st.code(result_package.get('content', 'N/A'), language='markdown')
                st.divider()
                with st.expander("🖼️ پرامپت تولید تصویر"):
                    st.code(result_package.get('image_prompt', 'N/A'), language=None)
                st.divider()
                with st.expander("📱 پیشنهادات استوری اینستاگرام"):
                    st.markdown("**عنوان استوری:**")
                    st.code(result_package.get('instagram_story_title', 'N/A'), language=None)
                    st.markdown("**توضیحات/تیزر استوری:**")
                    st.code(result_package.get('instagram_story_description', 'N/A'), language=None)
                st.success("Text generation complete!")
                st.divider()

                st.subheader("🖼️ Upload and Save Thumbnail Image")
                uploaded_image = st.file_uploader("Choose an image file (JPG, PNG, etc.)...", type=["jpg", "jpeg", "png"])
                
                if uploaded_image is not None:
                    target_filename = result_package.get('filename')
                    if target_filename:
                        try:
                            save_path = os.path.join(GRAPHIC_DIR, target_filename)
                            os.makedirs(GRAPHIC_DIR, exist_ok=True)
                            img = Image.open(uploaded_image)
                            st.image(img, caption="Uploaded Image", use_column_width=True)
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                                logging.info(f"Converted image mode from {img.mode} to RGB.")
                            logging.info(f"Attempting to save image to: {save_path}")
                            img.save(save_path, 'WEBP')
                            st.success(f"Image successfully saved as WebP to: {save_path}")
                        except Exception as img_e:
                            st.error(f"Error processing or saving image: {img_e}")
                            logging.exception(f"Error processing/saving uploaded image:")
                    else:
                        st.error("Could not determine the target filename from the generated results.")

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
                # Get SEO Title and Description from LLM output
                wp_seo_title = display_data.get('seo_title') # Use generated SEO title
                wp_seo_description = display_data.get('meta_description') # Use generated meta description
                wp_image_filename = display_data.get('filename') # Get expected image filename
                wp_image_alt_text = display_data.get('alt_text') # Get image alt text
                
                # Check if image exists
                wp_image_path = None
                if wp_image_filename:
                    expected_image_path = os.path.join(GRAPHIC_DIR, wp_image_filename)
                    if os.path.exists(expected_image_path):
                        wp_image_path = expected_image_path
                        st.info(f"Found image: {expected_image_path}")
                    else:
                        st.warning(f"Image file not found at expected path: {expected_image_path}. Please place the image there. The post will be created without a featured image.")
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
            pass 

    else:
        st.error("❌ LLM Client Initialization Failed. Cannot generate package.")
        st.warning("Please ensure the GOOGLE_API_KEY is correctly set in your .env file and check the application logs for specific errors.")

if __name__ == "__main__":
    main()