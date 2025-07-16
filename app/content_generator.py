import logging
import json
import re
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .file_utils import save_output_to_file_async, read_prompt_file_async

# Configure logging (can be configured centrally if preferred)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Blog Package Generation Function (Modified) ---
async def generate_persian_blog_package(
    llm_blog_client: ChatOpenAI,
    llm_image_prompt_client: ChatOpenAI,
    llm_instagram_text_client: ChatOpenAI,
    source_title: str,
    source_body: str,
    source_name: str,
    source_url: str,
    include_instagram_texts: bool = True,
    include_story_teasers: bool = True,
    include_iranian_video_prompt: bool = False
) -> dict:
    blog_package_content = {} # This will hold the blog content, meta, tags
    blog_llm_raw_output = None
    processed_output = None 
    blog_thumbnail_image_prompt = "Error: Default blog image prompt."
    instagram_video_prompt = "Error: Default Instagram video prompt."
    pantry_api_id = os.getenv("PANTRY_ID")
    iranian_farsi_video_prompt = "Error: Iranian Farsi video prompt not generated."

    # Load prompts from files
    try:
        system_prompt_blog_generation_template = await read_prompt_file_async("system_prompt_blog_generation.txt")
        human_prompt_blog_generation_template = await read_prompt_file_async("human_prompt_blog_generation.txt")

        # Format prompts with source data
        system_prompt_content = system_prompt_blog_generation_template
        human_prompt_content = human_prompt_blog_generation_template.format(source_title=source_title, source_body=source_body, source_name=source_name, source_url=source_url)

        messages = [
            SystemMessage(content=system_prompt_content),
            HumanMessage(content=human_prompt_content)
        ]

    except Exception as e:
        logging.exception(f"Error loading or formatting blog generation prompts from files: {e}")
        return {"error": f"Error loading or formatting prompts: {e}"}

    try:
        logging.info(f"Invoking LLM for Blog Content Generation (Source: {source_name}, Title: {source_title[:50]}...).)")
        response = await llm_blog_client.ainvoke(messages)
        blog_llm_raw_output = response.content 
        
        if not isinstance(blog_llm_raw_output, str):
            logging.error(f"LLM response content for blog generation was not a string: {type(blog_llm_raw_output)}")
            await save_output_to_file_async(
                raw_blog_output=str(blog_llm_raw_output), # Attempt to convert to string for logging
                raw_instagram_video_prompt=instagram_video_prompt,
                error=f"Blog content LLM response was not a string: {type(blog_llm_raw_output)}", 
                slug='non-string-response-blog',
                pantry_id=pantry_api_id
            )
            return {"error": f"Blog content LLM response was not a string: {type(blog_llm_raw_output)}"}

        logging.info("LLM for Blog Content Generation successful.")

        processed_output = blog_llm_raw_output.strip()
        if processed_output.startswith("```json"):
            processed_output = processed_output[7:]
        if processed_output.endswith("```"):
            processed_output = processed_output[:-3]
        processed_output = processed_output.strip()

        try:
            blog_package_content = json.loads(processed_output)
            logging.info("Successfully parsed JSON response from Blog LLM.")
            
            required_keys_blog = ["primary_focus_keyword", "secondary_focus_keyword", "additional_focus_keywords", "title", "seo_title", "slug", "meta_description", "alt_text", "tags", "content"]
            if not all(key in blog_package_content for key in required_keys_blog):
                missing_keys = list(set(required_keys_blog) - set(blog_package_content.keys()))
                logging.error(f"Missing required keys in parsed JSON for blog content: {missing_keys}")
                await save_output_to_file_async(
                    raw_blog_output=processed_output, 
                    raw_instagram_video_prompt=instagram_video_prompt,
                    error=f"Blog content JSON missing keys: {missing_keys}", 
                    slug='json-error-blog',
                    pantry_id=pantry_api_id # Pass pantry_id
                )
                return {"error": f"Blog content LLM response missing keys: {missing_keys}"}
            
            if not isinstance(blog_package_content.get('additional_focus_keywords'), list):
                logging.error(f"Invalid type for 'additional_focus_keywords': expected list")
                await save_output_to_file_async(
                    raw_blog_output=processed_output, 
                    raw_instagram_video_prompt=instagram_video_prompt,
                    error="Invalid type for additional_focus_keywords", 
                    slug='json-type-error-blog',
                    pantry_id=pantry_api_id # Pass pantry_id
                )
                return {"error": "Blog content LLM response has invalid type for additional_focus_keywords"}

            slug = blog_package_content.get('slug')
            if slug:
                blog_package_content['filename'] = f"hooshews.com-{slug}.webp" # For blog thumbnail
            else:
                blog_package_content['filename'] = "hooshews.com-missing-slug.webp"
                logging.warning("Slug key missing or empty in blog JSON, using default filename.")

        except json.JSONDecodeError as json_err:
            logging.warning(f"Initial JSON parsing failed: {json_err}. Attempting to fix literal newlines in JSON...")
            
            # Try to fix literal newlines in JSON string values
            try:
                # Step 1: Protect already escaped sequences
                temp_output = processed_output.replace('\\"', '__TEMP_QUOTE__')
                temp_output = temp_output.replace('\\n', '__TEMP_NEWLINE__')
                
                # Step 2: Find literal newlines inside JSON string values and escape them
                # This regex finds patterns like "key": "value with\nliteral newline" and fixes them
                
                # Replace literal newlines inside string values (between quotes)
                def fix_newlines_in_strings(match):
                    full_match = match.group(0)
                    # Replace literal newlines with \n inside the string value
                    return full_match.replace('\n', '\\n')
                
                # Pattern to match JSON string values that might contain literal newlines
                # This handles both simple and complex multi-line string values
                pattern = r'"[^"]*":\s*"(?:[^"\\]|\\.)*(?:\n(?:[^"\\]|\\.)*)*"'
                temp_output = re.sub(pattern, fix_newlines_in_strings, temp_output, flags=re.MULTILINE | re.DOTALL)
                
                # Step 3: Restore protected sequences
                temp_output = temp_output.replace('__TEMP_NEWLINE__', '\\n')
                temp_output = temp_output.replace('__TEMP_QUOTE__', '\\"')
                
                # Step 4: Remove any trailing commas
                temp_output = re.sub(r',(\s*[}\]])', r'\1', temp_output)
                
                logging.info(f"Fixed JSON (first 500 chars): {temp_output[:500]}...")
                
                blog_package_content = json.loads(temp_output)
                logging.info("Successfully parsed JSON after fixing literal newlines.")
                
            except json.JSONDecodeError as json_err2:
                logging.error(f"Failed to decode JSON even after newline fixes: {json_err2}. Raw (first 500 chars): {processed_output[:500]}...")
                await save_output_to_file_async(
                    raw_blog_output=processed_output, 
                    raw_instagram_video_prompt=instagram_video_prompt,
                    error=f"Blog content JSON decode error: {json_err2}", 
                    slug='json-decode-error-blog',
                    pantry_id=pantry_api_id
                )
                return {"error": f"Could not parse Blog LLM response as JSON: {json_err2}"}
            except Exception as fix_err:
                logging.error(f"Error while trying to fix JSON: {fix_err}. Raw (first 500 chars): {processed_output[:500]}...")
                await save_output_to_file_async(
                    raw_blog_output=processed_output, 
                    raw_instagram_video_prompt=instagram_video_prompt,
                    error=f"Blog content JSON fix error: {fix_err}", 
                    slug='json-fix-error-blog',
                    pantry_id=pantry_api_id
                )
                return {"error": f"Error while fixing Blog LLM JSON: {fix_err}"}
        
        # Initialize the final package with the blog content
        final_package = {**blog_package_content} # Start with content, meta, tags

        # Generate BOTH image prompts (blog thumbnail and Instagram post image)
        # These are added to the final_package but are generated by different prompts/logic
        if llm_image_prompt_client:
            if source_title and source_body: 
                blog_thumbnail_image_prompt = await generate_image_prompt( # For blog thumbnail
                    llm_client=llm_image_prompt_client,
                    header=source_title, # Use original source_title for blog thumbnail context
                    description=source_body # Use original source_body for blog thumbnail context
                )
                final_package['image_prompt'] = blog_thumbnail_image_prompt # Blog thumbnail prompt

                # Always generate static Instagram image prompt
                instagram_static_image_prompt = await generate_instagram_image_prompt( # For Instagram post image (static)
                    llm_client=llm_image_prompt_client,
                    header=source_title, # Can also use source_title for context here
                    description=source_body # Or specific snippets if preferred later
                )
                final_package['instagram_static_image_prompt'] = instagram_static_image_prompt

                # Always generate video-ready Instagram image prompt
                instagram_video_ready_image_prompt = await generate_instagram_image_prompt_for_video( # For Instagram post image (video-ready)
                    llm_client=llm_image_prompt_client,
                    header=source_title, # Can also use source_title for context here
                    description=source_body # Or specific snippets if preferred later
                )
                final_package['instagram_video_ready_image_prompt'] = instagram_video_ready_image_prompt
            else:
                final_package['image_prompt'] = "Error: Missing source for blog image prompt."
                final_package['instagram_static_image_prompt'] = "Error: Missing source for Instagram static image prompt."
                final_package['instagram_video_ready_image_prompt'] = "Error: Missing source for Instagram video-ready image prompt."
                logging.warning("Missing source_title or source_body for image prompt generation.")
        else:
            final_package['image_prompt'] = "Error: Blog image prompt LLM client not available."
            final_package['instagram_static_image_prompt'] = "Error: Instagram static image prompt LLM client not available."
            final_package['instagram_video_ready_image_prompt'] = "Error: Instagram video-ready image prompt LLM client not available."
            logging.error("Skipping image prompt generation; llm_image_prompt_client was None.")
        
        # --- NEW: Perform blog analysis for Instagram and Iranian video if needed ---
        derived_insta_inputs = {}
        if (include_instagram_texts or include_iranian_video_prompt) and llm_instagram_text_client and blog_package_content.get('content'):
            try:
                logging.info("Starting blog analysis for Instagram/Iranian video inputs...")
                
                derived_insta_inputs = await analyze_blog_for_instagram_inputs(
                    llm_client=llm_instagram_text_client, 
                    blog_title=blog_package_content.get('title', ''),
                    blog_content=blog_package_content.get('content', '')
                )
                logging.info(f"Blog analysis successful. Derived inputs: {derived_insta_inputs}")

            except Exception as analysis_e:
                logging.exception(f"An unexpected error occurred during blog analysis: {analysis_e}")
                derived_insta_inputs = {"error": f"Unexpected error during blog analysis: {analysis_e}", "derived_blog_topic": "", "derived_key_takeaways": [], "derived_core_emotion": "", "derived_cta_word": ""}
        else:
            logging.info("Blog analysis for Instagram/Iranian video skipped (not requested or missing data/LLM). ")
            derived_insta_inputs = {"error": "Blog analysis skipped or missing data.", "derived_blog_topic": "", "derived_key_takeaways": [], "derived_core_emotion": "", "derived_cta_word": ""}


        # --- Conditionally Generate Instagram Texts ---
        # Only run this section if include_instagram_texts is True
        if include_instagram_texts:
            try:
                logging.info("Starting Instagram text generation...")
                # Use derived_insta_inputs from the common analysis block
                if not derived_insta_inputs.get("error") and derived_insta_inputs.get("derived_blog_topic"):
                    # Ensure derived_key_takeaways is a list of strings
                    derived_key_takeaways_for_insta = [str(item) for item in derived_insta_inputs.get("derived_key_takeaways", []) if isinstance(item, (str, int, float, bool))]

                    # Load prompts for Instagram post texts
                    system_prompt_instagram_texts_template = await read_prompt_file_async("system_prompt_instagram_texts.txt")
                    human_prompt_instagram_texts_template = await read_prompt_file_async("human_prompt_instagram_texts.txt")

                    takeaways_formatted_for_insta = "\n".join([f"    * {point}" for point in derived_key_takeaways_for_insta])

                    human_prompt_content_insta = human_prompt_instagram_texts_template.format(
                        derived_blog_topic=derived_insta_inputs.get("derived_blog_topic", ""),
                        takeaways_formatted=takeaways_formatted_for_insta,
                        derived_cta_word=derived_insta_inputs.get("derived_cta_word", ""),
                        derived_core_emotion=derived_insta_inputs.get("derived_core_emotion", "")
                    )

                    messages_insta = [
                        SystemMessage(content=system_prompt_instagram_texts_template),
                        HumanMessage(content=human_prompt_content_insta)
                    ]

                    response_insta = await llm_instagram_text_client.ainvoke(messages_insta)
                    raw_output_insta = response_insta.content

                    if isinstance(raw_output_insta, str):
                        insta_texts = {} # Initialize in this scope
                        cleaned_output_insta = raw_output_insta.strip()
                        if cleaned_output_insta.startswith("```json") or cleaned_output_insta.startswith("```"):
                            cleaned_output_insta = cleaned_output_insta[cleaned_output_insta.find("{"):cleaned_output_insta.rfind("}") + 1]
                        
                        try:
                            insta_texts = json.loads(cleaned_output_insta)
                        except json.JSONDecodeError as jde:
                            logging.warning(f"JSON parsing failed for Instagram texts after ALL cleaning attempts ({str(jde)}). Raw cleaned output: {cleaned_output_insta[:200]}...")
                            title_match = re.search(r'"instagram_post_title":\s*"(.*?)"', cleaned_output_insta, re.DOTALL)
                            caption_match = re.search(r'"instagram_post_caption":\s*"(.*?)"', cleaned_output_insta, re.DOTALL)
                            if title_match and caption_match:
                                insta_texts = {
                                    "instagram_post_title": title_match.group(1).strip(),
                                    "instagram_post_caption": caption_match.group(1).strip()
                                }
                                logging.info("Successfully extracted Instagram texts using fallback regex.")
                            else:
                                logging.error(f"Could not parse Instagram texts with regex fallback. Title match: {bool(title_match)}, Caption match: {bool(caption_match)}. Raw: {cleaned_output_insta[:200]}")
                                insta_texts = {"error": "Could not parse Instagram texts from LLM (regex fallback failed)"}
                        except Exception as e:
                            logging.error(f"An unexpected error occurred during Instagram text parsing: {e}")
                            insta_texts = {"error": f"Instagram text parsing failed - {e}"}

                    if insta_texts.get("error"):
                        logging.error(f"Error during Instagram text generation: {insta_texts.get('error')}")
                        final_package['instagram_post_title'] = f"Error: Instagram text generation failed - {insta_texts.get('error')}"
                        final_package['instagram_post_caption'] = f"Error: Instagram text generation failed - {insta_texts.get('error')}"
                        final_package['instagram_video_prompt'] = "Instagram video prompt not generated (Instagram texts disabled by user)."
                    else:
                        logging.info("Instagram text generation complete.")
                        final_package['instagram_post_title'] = insta_texts.get('instagram_post_title')
                        final_package['instagram_post_caption'] = insta_texts.get('instagram_post_caption')
                        
                        if llm_image_prompt_client and insta_texts.get('instagram_post_caption'): # Simplified check
                            try:
                                logging.info("Starting Instagram video prompt generation...")
                                instagram_video_prompt = await generate_instagram_video_prompt(
                                    llm_client=llm_image_prompt_client,
                                    header=source_title,
                                    description=source_body,
                                            instagram_caption=insta_texts.get('instagram_post_caption', "")
                                )
                                final_package['instagram_video_prompt'] = instagram_video_prompt
                                logging.info("Instagram video prompt generation complete.")
                            except Exception as video_prompt_e:
                                logging.exception(f"Error during Instagram video prompt generation: {video_prompt_e}")
                                final_package['instagram_video_prompt'] = f"Error generating Instagram video prompt: {video_prompt_e}"
                        else:
                            final_package['instagram_video_prompt'] = "Error: Missing required data for Instagram video prompt generation (Instagram texts enabled)."
                            logging.warning("Skipping Instagram video prompt generation due to missing requirements (Instagram texts enabled).")

                else:
                    # This else corresponds to 'if not derived_insta_inputs.get("error") and derived_insta_inputs.get("derived_blog_topic"):'
                    final_package['instagram_post_title'] = "Error: Instagram text generation skipped due to blog analysis error or missing data."
                    final_package['instagram_post_caption'] = "Error: Instagram text generation skipped due to blog analysis error or missing data."
                    final_package['instagram_video_prompt'] = "Instagram video prompt not generated (blog analysis failed or texts disabled)."
                    logging.warning("Instagram text generation skipped due to blog analysis error or missing data.")

            except Exception as insta_gen_e:
                logging.exception(f"An unexpected error occurred during Instagram text generation: {insta_gen_e}")
                final_package['instagram_post_title'] = f"Error: Instagram text generation failed - {insta_gen_e}"
                final_package['instagram_post_caption'] = f"Error: Instagram text generation failed - {insta_gen_e}"
                final_package['instagram_video_prompt'] = "Instagram video prompt not generated (Instagram texts disabled by user)."

        # If Instagram texts were not generated because include_instagram_texts is False, set default error messages
        if not include_instagram_texts:
            final_package['instagram_post_title'] = "Instagram post title not generated (disabled by user)."
            final_package['instagram_post_caption'] = "Instagram post caption not generated (disabled by user)."
            final_package['instagram_video_prompt'] = "Instagram video prompt not generated (Instagram texts disabled by user)."
                
        # --- Conditionally Generate Instagram Story Teasers ---
        # Only run this section if include_story_teasers is True and LLM client is available and blog content is available
        if include_story_teasers and llm_instagram_text_client and blog_package_content.get('content'):
            try:
                logging.info("Starting Instagram Story teaser generation...")
                # Load prompts for Instagram story teasers
                system_prompt_story_template = await read_prompt_file_async("system_prompt_instagram_story_teasers.txt")
                human_prompt_story_template = await read_prompt_file_async("human_prompt_instagram_story_teasers.txt")

                human_prompt_content_story = human_prompt_story_template.format(
                    blog_content=blog_package_content.get('content', '')
                )

                messages_story = [
                    SystemMessage(content=system_prompt_story_template),
                    HumanMessage(content=human_prompt_content_story)
                ]

                response_story = await llm_instagram_text_client.ainvoke(messages_story)
                raw_output_story = response_story.content

                if isinstance(raw_output_story, str):
                    story_teasers_result = {} # Initialize in this scope
                    story_teasers_result["raw_output"] = raw_output_story
                    logging.info(f"LLM for Instagram Story Teasers successful. Raw output: {raw_output_story[:200]}...")

                    try:
                        cleaned_output_story = raw_output_story.strip()
                        if cleaned_output_story.startswith("```json"):
                            cleaned_output_story = cleaned_output_story[7:]
                        if cleaned_output_story.endswith("```"):
                            cleaned_output_story = cleaned_output_story[:-3]
                        cleaned_output_story = cleaned_output_story.strip()

                        parsed_json_story = json.loads(cleaned_output_story)
                        story_teasers_result["story_main_title"] = parsed_json_story.get("story_main_title", "Error: Missing main title")
                        story_teasers_result["story_subtitle"] = parsed_json_story.get("story_subtitle", "Error: Missing subtitle")
                        story_teasers_result["story_body_text"] = parsed_json_story.get("story_body_text", "Error: Missing body text")
                        if not (parsed_json_story.get("story_main_title") and parsed_json_story.get("story_subtitle") and parsed_json_story.get("story_body_text")):
                            story_teasers_result["error"] = "One or more required fields missing in story teaser JSON."
                            logging.error(f"Story Teaser JSON missing fields. Parsed: {parsed_json_story}")
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to decode JSON from Story Teaser LLM: {e}. Raw: {raw_output_story}")
                        story_teasers_result["error"] = f"Could not parse Story Teaser LLM response as JSON: {e}"
                        title_match = re.search(r'"story_main_title":\s*"(.*?)"', raw_output_story, re.DOTALL)
                        subtitle_match = re.search(r'"story_subtitle":\s*"(.*?)"', raw_output_story, re.DOTALL)
                        body_match = re.search(r'"story_body_text":\s*"(.*?)"', raw_output_story, re.DOTALL)

                        if title_match:
                            story_teasers_result["story_main_title"] = title_match.group(1).strip()
                        else:
                            story_teasers_result["story_main_title"] = "Error: Could not extract main title (regex)"
                        
                        if subtitle_match:
                            story_teasers_result["story_subtitle"] = subtitle_match.group(1).strip()
                        else:
                            story_teasers_result["story_subtitle"] = "Error: Could not extract subtitle (regex)"

                        if body_match:
                            story_teasers_result["story_body_text"] = body_match.group(1).strip()
                        else:
                            story_teasers_result["story_body_text"] = "Error: Could not extract body text (regex)"
                        
                        if not (title_match and subtitle_match and body_match):
                            logging.warning("Fallback regex extraction for story teasers failed or was incomplete.")
                            current_error = story_teasers_result.get("error", "")
                            story_teasers_result["error"] = f"{current_error} | Regex extraction also failed or incomplete.".strip(" | ")
                        else:
                            logging.info("Successfully extracted story teaser fields using fallback regex.")
                            story_teasers_result["error"] = None 
                else:
                    logging.error(f"LLM response content for Instagram story teasers was not a string: {type(raw_output_story)}")
                    story_teasers_result = {"error": "LLM response content for Instagram story teasers not string.", "story_main_title": "Error: Generation failed (non-string output)", "story_subtitle": "Error: Generation failed (non-string output)", "story_body_text": "Error: Generation failed (non-string output)"}
                final_package['instagram_story_teasers'] = story_teasers_result
                logging.info("Instagram Story teaser generation complete.")

            except Exception as insta_story_gen_e:
                logging.exception(f"An unexpected error occurred during Instagram Story teaser generation: {insta_story_gen_e}")
                final_package['instagram_story_teasers'] = {"error": f"Error generating Instagram Story teasers: {insta_story_gen_e}"}

        elif not include_story_teasers:
             logging.info("Instagram Story teaser generation skipped by user.")
             final_package['instagram_story_teasers'] = {"error": "Instagram Story teaser generation skipped by user."}
        elif not llm_instagram_text_client:
             logging.warning("Skipping Instagram Story teaser generation; llm_instagram_text_client was None.")
             final_package['instagram_story_teasers'] = {"error": "Instagram text LLM client not available for story teasers."}
        elif not blog_package_content.get('content'):
             logging.warning("Skipping Instagram Story teaser generation; blog content not available.")
             final_package['instagram_story_teasers'] = {"error": "Blog content not available for story teasers."}

        # --- NEW: Conditionally Generate Iranian Farsi Video Prompt ---
        # Use derived_insta_inputs for blog_topic and key_takeaways
        if include_iranian_video_prompt and llm_instagram_text_client and not derived_insta_inputs.get("error") and derived_insta_inputs.get("derived_blog_topic"):
            try:
                logging.info("Starting Iranian Farsi video prompt generation...")
                # Load prompts for Iranian Farsi video
                system_prompt_iranian_video_template = await read_prompt_file_async("system_prompt_iranian_video.txt")
                human_prompt_iranian_video_template = await read_prompt_file_async("human_prompt_iranian_video.txt")

                # Ensure key_takeaways is a list of strings for formatting
                key_takeaways_for_iranian_video = [str(item) for item in derived_insta_inputs.get("derived_key_takeaways", []) if isinstance(item, (str, int, float, bool))]
                key_takeaways_formatted_for_iranian_video = "\n".join([f"    * {point}" for point in key_takeaways_for_iranian_video])

                human_prompt_content_iranian_video = human_prompt_iranian_video_template.format(
                    blog_topic=derived_insta_inputs.get("derived_blog_topic", ""),
                    key_takeaways_formatted=key_takeaways_formatted_for_iranian_video
                )

                messages_iranian_video = [
                    SystemMessage(content=system_prompt_iranian_video_template),
                    HumanMessage(content=human_prompt_content_iranian_video)
                ]

                response_iranian_video = await llm_instagram_text_client.ainvoke(messages_iranian_video)
                prompt_output_iranian_video = response_iranian_video.content

                if isinstance(prompt_output_iranian_video, str):
                    iranian_farsi_video_prompt = prompt_output_iranian_video.strip()
                    logging.info("Iranian Farsi Video Prompt LLM invocation successful.")
                else:
                    logging.error(f"LLM response content for Iranian Farsi video prompt was not a string: {type(prompt_output_iranian_video)}")
                    iranian_farsi_video_prompt = "Error: LLM response content for Iranian Farsi video prompt not string."

                final_package['iranian_farsi_video_prompt'] = iranian_farsi_video_prompt
            except Exception as iranian_video_e:
                logging.exception(f"Error during Iranian Farsi video prompt generation: {iranian_video_e}")
                final_package['iranian_farsi_video_prompt'] = f"Error generating Iranian Farsi video prompt: {iranian_video_e}"
        elif not include_iranian_video_prompt:
            logging.info("Iranian Farsi video prompt generation skipped by user.")
            final_package['iranian_farsi_video_prompt'] = "Iranian Farsi video prompt not generated (disabled by user)."
        elif not llm_instagram_text_client:
            logging.warning("Skipping Iranian Farsi video prompt generation; llm_instagram_text_client was None.")
            final_package['iranian_farsi_video_prompt'] = "Error: LLM client not available for Iranian Farsi video prompt."
        elif derived_insta_inputs.get("error") or not derived_insta_inputs.get("derived_blog_topic"):
            logging.warning("Skipping Iranian Farsi video prompt generation; blog analysis failed or missing data.")
            final_package['iranian_farsi_video_prompt'] = "Error: Blog analysis data not available for Iranian Farsi video prompt."

        await save_output_to_file_async(
            raw_blog_output=blog_llm_raw_output,
            raw_image_prompt=blog_thumbnail_image_prompt, # Use the initialized variable
            raw_instagram_post_image_prompt=final_package.get('instagram_static_image_prompt'), # Pass the static image prompt
            raw_instagram_video_prompt=final_package.get('instagram_video_ready_image_prompt'), # Pass the video-ready image prompt
            raw_iranian_farsi_video_prompt=final_package.get('iranian_farsi_video_prompt'), # NEW: Pass the Iranian Farsi video prompt
            parsed_package=final_package,
            slug=final_package.get('slug', 'no-slug-blog-pkg'),
            pantry_id=pantry_api_id # Pass pantry_id
        )
        return final_package # Return the package with blog content and both image prompts

    except Exception as e:
        logging.exception(f"Error during Persian blog package generation: {e}")
        pantry_api_id_error = os.getenv("PANTRY_ID") 
        await save_output_to_file_async(
            raw_blog_output=blog_llm_raw_output, 
            raw_image_prompt=blog_thumbnail_image_prompt, # Ensure these are passed even on early error
            raw_instagram_post_image_prompt=final_package.get('instagram_static_image_prompt', "Error during generation"), # Pass the static image prompt
            raw_instagram_video_prompt=final_package.get('instagram_video_ready_image_prompt', "Error during generation"), # Pass the video-ready image prompt
            raw_iranian_farsi_video_prompt=final_package.get('iranian_farsi_video_prompt', "Error during generation"), # NEW: Pass the Iranian Farsi video prompt
            error=str(e), 
            slug='error-blog-pkg',
            pantry_id=pantry_api_id_error # Pass pantry_id
        ) 
        return {"error": f"Error generating Persian blog package: {e}"}


# --- Image Prompt Generation Function ---
async def generate_image_prompt(llm_client: ChatOpenAI, header: str, description: str) -> str:
    """ Docstring for generate_image_prompt """
    try:
        prompt_fstring_template = await read_prompt_file_async("blog_thumbnail_image_prompt.txt")
        prompt_fstring = prompt_fstring_template.format(header=header, description=description)
    except Exception as e:
        logging.exception(f"Error loading or formatting blog thumbnail image prompt: {e}")
        return f"Error loading or formatting blog thumbnail image prompt: {e}"

    messages = [HumanMessage(content=prompt_fstring)]
    try:
        logging.info(f"Invoking Image Prompt LLM (async)...")
        response = await llm_client.ainvoke(messages) # Ensure response is assigned here
        if isinstance(response.content, str):
            logging.info("Image Prompt LLM invocation successful (async).")
            return response.content.strip()
        else:
            logging.error(f"LLM response content for image prompt was not a string: {type(response.content)}")
            return "Error: LLM response content for image prompt not string."
    except Exception as e:
        logging.exception(f"Error during async Image Prompt LLM invocation: {e}")
        return f"Error generating image prompt: {e}"

# --- Instagram Image Prompt Generation Function (Static) ---
async def generate_instagram_image_prompt(llm_client: ChatOpenAI, header: str, description: str) -> str:
    """Generate a professional, satirical, witty, and visually bold image prompt for a static Instagram post about tech/AI."""
    try:
        prompt_fstring_template = await read_prompt_file_async("instagram_static_image_prompt.txt")
        prompt_fstring = prompt_fstring_template.format(header=header, description=description)
    except Exception as e:
        logging.exception(f"Error loading or formatting Instagram static image prompt: {e}")
        return f"Error loading or formatting Instagram static image prompt: {e}"

    messages = [HumanMessage(content=prompt_fstring)]
    try:
        logging.info(f"Invoking Instagram Image Prompt LLM (async) for static image...")
        response = await llm_client.ainvoke(messages)
        if isinstance(response.content, str):
            logging.info("Instagram Image Prompt LLM invocation successful (async) for static image.")
            return response.content.strip()
        else:
            logging.error(f"LLM response content for static Instagram image prompt was not a string: {type(response.content)}")
            return "Error: LLM response content for static Instagram image prompt not string."
    except Exception as e:
        logging.exception(f"Error during async Instagram Image Prompt LLM invocation: {e}")
        return f"Error generating Instagram image prompt: {e}"

# --- Instagram Image Prompt Generation Function (Video-Ready) ---
async def generate_instagram_image_prompt_for_video(llm_client: ChatOpenAI, header: str, description: str) -> str:
    """Generate a professional, satirical, witty, and visually bold image prompt for an Instagram post optimized for video generation."""
    try:
        prompt_fstring_template = await read_prompt_file_async("instagram_video_ready_image_prompt.txt")
        prompt_fstring = prompt_fstring_template.format(header=header, description=description)
    except Exception as e:
        logging.exception(f"Error loading or formatting Instagram video-ready image prompt: {e}")
        return f"Error loading or formatting Instagram video-ready image prompt: {e}"

    messages = [HumanMessage(content=prompt_fstring)]
    try:
        logging.info(f"Invoking Instagram Image Prompt LLM (async) for video-ready image...")
        response = await llm_client.ainvoke(messages)
        if isinstance(response.content, str):
            logging.info("Instagram Image Prompt LLM invocation successful (async) for video-ready image.")
            return response.content.strip()
        else:
            logging.error(f"LLM response content for video-ready Instagram image prompt was not a string: {type(response.content)}")
            return "Error: LLM response content for video-ready Instagram image prompt not string."
    except Exception as e:
        logging.exception(f"Error during async Instagram Image Prompt LLM invocation: {e}")
        return f"Error generating Instagram image prompt for video: {e}"

# --- Instagram Video Generation Prompt Function ---
async def generate_instagram_video_prompt(llm_client: ChatOpenAI, header: str, description: str, instagram_caption: str) -> str:
    """Generate a professional video generation prompt following Veo 2 best practices for creating viral Instagram videos from static photos."""
    try:
        prompt_fstring_template = await read_prompt_file_async("instagram_video_prompt.txt")
        prompt_fstring = prompt_fstring_template.format(header=header, description=description, instagram_caption=instagram_caption)
    except Exception as e:
        logging.exception(f"Error loading or formatting Instagram video prompt: {e}")
        return f"Error loading or formatting Instagram video prompt: {e}"

    messages = [HumanMessage(content=prompt_fstring)]
    try:
        logging.info(f"Invoking Instagram Video Prompt LLM (async) using Veo 2 best practices...")
        response = await llm_client.ainvoke(messages)
        if isinstance(response.content, str):
            logging.info("Instagram Video Prompt LLM invocation successful (async) - Veo 2 optimized.")
            return response.content.strip()
        else:
            logging.error(f"LLM response content for Instagram video prompt was not a string: {type(response.content)}")
            return "Error: LLM response content for Instagram video prompt not string."
    except Exception as e:
        logging.exception(f"Error during async Instagram Video Prompt LLM invocation: {e}")
        return f"Error generating Instagram video prompt: {e}"

# --- New Instagram Post Text Generation Function (Using Specific Template) ---
async def generate_instagram_post_texts(llm_client: ChatOpenAI, derived_blog_topic: str, derived_key_takeaways: list[str], derived_cta_word: str, derived_core_emotion: str) -> dict:
    """Generates Instagram Viral Post Title and Engaging Caption using AI-derived inputs and a detailed template."""
    
    takeaways_formatted = "\n".join([f"    * {point}" for point in derived_key_takeaways])

    # Load prompts from files
    try:
        system_prompt_instagram_texts_template = await read_prompt_file_async("system_prompt_instagram_texts.txt")
        human_prompt_instagram_texts_template = await read_prompt_file_async("human_prompt_instagram_texts.txt")

        system_prompt_instagram_texts = system_prompt_instagram_texts_template
        human_prompt_instagram_texts = human_prompt_instagram_texts_template.format(
            derived_blog_topic=derived_blog_topic,
            takeaways_formatted=takeaways_formatted,
            derived_cta_word=derived_cta_word,
            derived_core_emotion=derived_core_emotion
        )

    except Exception as e:
        logging.exception(f"Error loading or formatting Instagram text prompts from files: {e}")
        return {"error": f"Error loading or formatting Instagram text prompts: {e}"}

    messages = [
        SystemMessage(content=system_prompt_instagram_texts),
        HumanMessage(content=human_prompt_instagram_texts)
    ]
    instagram_texts = {}
    try:
        logging.info(f"Invoking LLM for Instagram Post Texts (Derived Topic: {derived_blog_topic[:50]}...)...")
        response = await llm_client.ainvoke(messages)
        raw_output = str(response.content) # Ensure raw_output is always a string
        
        cleaned_output = raw_output.strip()
        if cleaned_output.startswith("```json") or cleaned_output.startswith("```"):
            cleaned_output = cleaned_output[cleaned_output.find("{"):cleaned_output.rfind("}") + 1]
        
        try:
            instagram_texts = json.loads(cleaned_output)
            return instagram_texts
        except json.JSONDecodeError as jde:
            logging.warning(f"JSON parsing failed for Instagram texts after ALL cleaning attempts ({str(jde)}). Raw cleaned output: {cleaned_output[:200]}...")
            title_match = re.search(r'"instagram_post_title":\s*"(.*?)"', cleaned_output, re.DOTALL)
            caption_match = re.search(r'"instagram_post_caption":\s*"(.*?)"', cleaned_output, re.DOTALL)
            if title_match and caption_match:
                instagram_texts = {
                    "instagram_post_title": title_match.group(1).strip(),
                    "instagram_post_caption": caption_match.group(1).strip()
                }
                logging.info("Successfully extracted Instagram texts using fallback regex.")
                return instagram_texts
            else:
                logging.error(f"Could not parse Instagram texts with regex fallback. Title match: {bool(title_match)}, Caption match: {bool(caption_match)}. Raw: {cleaned_output[:200]}")
                raise ValueError("Could not parse Instagram texts from LLM (regex fallback failed)")
    except Exception as e:
        logging.error(f"Error during Instagram text generation: {str(e)}")
        raise

async def analyze_blog_for_instagram_inputs(llm_client: ChatOpenAI, blog_title: str, blog_content: str) -> dict:
    
    # Load prompts for blog analysis
    try:
        system_prompt_analyze_blog_template = await read_prompt_file_async("system_prompt_analyze_blog.txt")
        human_prompt_analyze_blog_template = await read_prompt_file_async("human_prompt_analyze_blog.txt")

        # Format human prompt with blog content
        human_prompt_content_analyze = human_prompt_analyze_blog_template.format(
            blog_title=blog_title,
            blog_content=blog_content
        )

    except Exception as e:
        logging.exception(f"Error loading or formatting blog analysis prompts from files: {e}")
        return {"error": f"Error loading or formatting blog analysis prompts: {e}", "derived_blog_topic": "", "derived_key_takeaways": [], "derived_core_emotion": "", "derived_cta_word": ""}

    messages_analyze = [
        SystemMessage(content=system_prompt_analyze_blog_template),
        HumanMessage(content=human_prompt_content_analyze)
    ]
    derived_inputs = {}
    try:
        logging.info(f"Invoking LLM for Blog Analysis for Instagram Inputs (Title: {blog_title[:50]}...)...")
        response = await llm_client.ainvoke(messages_analyze)
        raw_output = str(response.content) # Ensure raw_output is always a string
        
        # Rest of the code for parsing and error handling
        raw_output = raw_output.strip()
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()

        try:
            parsed_json = json.loads(raw_output)
            required_keys = ["derived_blog_topic", "derived_key_takeaways", "derived_core_emotion", "derived_cta_word"]
            if isinstance(parsed_json, dict) and all(key in parsed_json for key in required_keys):
                if not isinstance(parsed_json.get("derived_key_takeaways"), list):
                    logging.error(f"Invalid type for 'derived_key_takeaways': expected list, got {type(parsed_json.get('derived_key_takeaways'))}. Output: {raw_output}")
                    derived_inputs = {"error": "Derived key takeaways is not a list."}
                else:
                    # Ensure derived_key_takeaways is list of strings
                    parsed_json['derived_key_takeaways'] = [str(item) for item in parsed_json.get('derived_key_takeaways', []) if isinstance(item, (str, int, float, bool))]
                    derived_inputs = parsed_json
                    logging.info("Successfully parsed JSON response from Blog Analysis.")
            else:
                logging.error(f"Could not find required keys in JSON from Blog Analysis LLM: {raw_output}")
                derived_inputs = {"error": "LLM response from Blog Analysis missing required keys."}
        except json.JSONDecodeError as json_err:
            logging.error(f"Failed to decode JSON from Blog Analysis LLM response: {json_err}. Raw: {raw_output}")
            derived_inputs = {"error": f"Could not parse Blog Analysis response from LLM. See logs."}

    except Exception as e:
        logging.exception(f"Error during Blog Analysis for Instagram Inputs: {e}")
        derived_inputs = {"error": f"Error during Blog Analysis: {e}", "derived_blog_topic": "", "derived_key_takeaways": [], "derived_core_emotion": "", "derived_cta_word": ""}
    
    return derived_inputs

async def generate_iranian_farsi_video_prompt(
    llm_client: ChatOpenAI,
    blog_topic: str,
    key_takeaways: list[str]
) -> str:
    logging.info("Starting independent Iranian Farsi video prompt generation...")

    # Load prompts for Iranian Farsi video
    try:
        system_prompt_iranian_video_template = await read_prompt_file_async("system_prompt_iranian_video.txt")
        human_prompt_iranian_video_template = await read_prompt_file_async("human_prompt_iranian_video.txt")

        # Ensure key_takeaways is a list of strings for formatting
        key_takeaways_for_iranian_video = [str(item) for item in key_takeaways if isinstance(item, (str, int, float, bool))]
        key_takeaways_formatted_for_iranian_video = "\n".join([f"    * {point}" for point in key_takeaways_for_iranian_video])

        human_prompt_content_iranian_video = human_prompt_iranian_video_template.format(
            blog_topic=blog_topic,
            key_takeaways_formatted=key_takeaways_formatted_for_iranian_video
        )

    except Exception as e:
        logging.exception(f"Error loading or formatting Iranian Farsi video prompts from files: {e}")
        return f"Error loading or formatting Iranian Farsi video prompts: {e}"

    messages_iranian_video = [
        SystemMessage(content=system_prompt_iranian_video_template),
        HumanMessage(content=human_prompt_content_iranian_video)
    ]

    try:
        logging.info("Invoking LLM for Iranian Farsi Video Prompt...")
        response = await llm_client.ainvoke(messages_iranian_video)
        prompt_output_iranian_video = response.content # Assign raw content first

        if isinstance(prompt_output_iranian_video, str):
            iranian_farsi_video_prompt = prompt_output_iranian_video.strip()
            logging.info("Iranian Farsi Video Prompt LLM invocation successful.")
        else:
            logging.error(f"LLM response content for Iranian Farsi video prompt was not a string: {type(prompt_output_iranian_video)}")
            iranian_farsi_video_prompt = "Error: LLM response content for Iranian Farsi video prompt not string."
        return iranian_farsi_video_prompt

    except Exception as iranian_video_e:
        logging.exception(f"Error during Iranian Farsi video prompt generation: {iranian_video_e}")
        return f"Error generating Iranian Farsi video prompt: {iranian_video_e}" 

async def generate_instagram_story_teasers(
    llm_client: ChatOpenAI,
    blog_content: str
) -> dict:
    logging.info("Starting Instagram Story Teaser generation...")

    # Load prompts for Instagram story teasers
    try:
        system_prompt_story_template = await read_prompt_file_async("system_prompt_instagram_story_teasers.txt")
        human_prompt_story_template = await read_prompt_file_async("human_prompt_instagram_story_teasers.txt")

        human_prompt_content_story = human_prompt_story_template.format(
            blog_content=blog_content
        )

    except Exception as e:
        logging.exception(f"Error loading or formatting Instagram story teaser prompts from files: {e}")
        return {"error": f"Error loading or formatting Instagram story teaser prompts: {e}"}

    messages_story = [
        SystemMessage(content=system_prompt_story_template),
        HumanMessage(content=human_prompt_content_story)
    ]

    story_teasers = {
        "story_main_title": "N/A",
        "story_subtitle": "N/A",
        "story_body_text": "N/A",
        "error": None,
        "raw_output": None
    }

    try:
        logging.info(f"Invoking LLM for Instagram Story Teasers (model: {llm_client.model_name})...")
        response_story = await llm_client.ainvoke(messages_story)
        raw_output_story = str(response_story.content)
        
        story_teasers["raw_output"] = raw_output_story
        logging.info(f"LLM for Instagram Story Teasers successful. Raw output: {raw_output_story[:200]}...")

        try:
            cleaned_output_story = raw_output_story.strip()
            if cleaned_output_story.startswith("```json"):
                cleaned_output_story = cleaned_output_story[7:]
            if cleaned_output_story.endswith("```"):
                cleaned_output_story = cleaned_output_story[:-3]
            cleaned_output_story = cleaned_output_story.strip()

            parsed_json_story = json.loads(cleaned_output_story)
            story_teasers["story_main_title"] = parsed_json_story.get("story_main_title", "Error: Missing main title")
            story_teasers["story_subtitle"] = parsed_json_story.get("story_subtitle", "Error: Missing subtitle")
            story_teasers["story_body_text"] = parsed_json_story.get("story_body_text", "Error: Missing body text")
            if not (parsed_json_story.get("story_main_title") and parsed_json_story.get("story_subtitle") and parsed_json_story.get("story_body_text")):
                story_teasers["error"] = "One or more required fields missing in story teaser JSON."
                logging.error(f"Story Teaser JSON missing fields. Parsed: {parsed_json_story}")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from Story Teaser LLM: {e}. Raw: {raw_output_story}")
            story_teasers["error"] = f"Could not parse Story Teaser LLM response as JSON: {e}"
            title_match = re.search(r'"story_main_title":\s*"(.*?)"', raw_output_story, re.DOTALL)
            subtitle_match = re.search(r'"story_subtitle":\s*"(.*?)"', raw_output_story, re.DOTALL)
            body_match = re.search(r'"story_body_text":\s*"(.*?)"', raw_output_story, re.DOTALL)

            if title_match:
                story_teasers["story_main_title"] = title_match.group(1).strip()
            else:
                story_teasers["story_main_title"] = "Error: Could not extract main title (regex)"
            
            if subtitle_match:
                story_teasers["story_subtitle"] = subtitle_match.group(1).strip()
            else:
                story_teasers["story_subtitle"] = "Error: Could not extract subtitle (regex)"

            if body_match:
                story_teasers["story_body_text"] = body_match.group(1).strip()
            else:
                story_teasers["story_body_text"] = "Error: Could not extract body text (regex)"
            
            if not (title_match and subtitle_match and body_match):
                logging.warning("Fallback regex extraction for story teasers failed or was incomplete.")
                current_error = story_teasers.get("error", "")
                story_teasers["error"] = f"{current_error} | Regex extraction also failed or incomplete.".strip(" | ")
            else:
                logging.info("Successfully extracted story teaser fields using fallback regex.")
                story_teasers["error"] = None 
    except Exception as e:
        logging.exception("An unexpected error occurred during Instagram Story Teaser generation.")
        story_teasers = {"error": f"Unexpected error in story teaser generation: {e}", "story_main_title": "Error: Generation failed", "story_subtitle": "Error: Generation failed", "story_body_text": "Error: Generation failed"}

    return story_teasers 