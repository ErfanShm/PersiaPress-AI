import logging
import json
import re
import os # Ensure os is imported
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage # AIMessage is not used directly here.
# Import a_s_y_n_c version of save_output_to_file
from .file_utils import save_output_to_file_async # MODIFIED

# Configure logging (can be configured centrally if preferred)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Blog Package Generation Function (Modified) ---
async def generate_persian_blog_package(
    llm_blog_client: ChatOpenAI,
    llm_image_prompt_client: ChatOpenAI,
    llm_instagram_text_client: ChatOpenAI, # Added new client
    source_title: str,
    source_body: str,
    source_name: str,
    source_url: str,
    include_instagram_texts: bool = True, # Added new parameter with default value
    include_story_teasers: bool = True # Added new parameter for story generation
) -> dict:
    """ 
    Generates blog content, SEO metadata, blog thumbnail image prompt, 
    Instagram post image prompt, Instagram post title, and Instagram post caption.
    """

    # --- System Prompt for Blog Generation ---
    system_prompt_blog_generation = f"""
Objective: As an expert SEO Content Strategist specializing in engaging, humanized Persian content, generate a highly SEO-optimized blog post for hooshews.com. It's crucial this post has excellent SEO (aiming for a high Rank Math score) so people can find the site on Google. The post must be written entirely in humanized Persian, focusing strongly on SEO best practices for keyword selection (including LSI keywords), structure, metadata, and visual appeal, and conclude with source attribution.

Language and Tone:
Language: Entirely in Persian (Farsi) (except for the پیوندیکتا and specific English terms as instructed in the user prompt). Use Persian numerals (۱, ۲, ۳...).
Style: Natural, humanized, friendly, and engaging. Avoid overly formal or robotic language. Write conversationally, as if explaining to a friend (like a journal entry). Make it accessible.

Output Format & Style (for this Blog Generation task):
Provide the entire output strictly as a **single JSON object**. Do **NOT** include any text before or after the JSON object. Do **NOT** use markdown code fences.
The JSON object should have ONLY the following keys for the blog content:
*   `"primary_focus_keyword"`: [Generated Persian Primary Focus Keyword]
*   `"secondary_focus_keyword"`: [Generated Persian Secondary Focus Keyword]
*   `"additional_focus_keywords"`: [Array of up to 2 additional Persian Keywords, or []]
*   `"title"`: [Generated Persian H1 Title]
*   `"seo_title"`: [Generated Persian SEO Title]
*   `"slug"`: [Generated English Slug]
*   `"meta_description"`: [Generated Persian Meta Description]
*   `"alt_text"`: [Generated Persian Alt Text for the BLOG thumbnail image]
*   `"tags"`: [Array of up to 7 Tag Strings]
*   `"content"`: [Generated Persian Blog Post Content as Markdown]
Ensure all string values in the JSON are properly escaped if necessary.
"""

    # --- Human Prompt for Blog Generation (Task-Specific) ---
    # This main_prompt is for the BLOG CONTENT generation ONLY.
    # It should NOT request instagram_post_title or instagram_post_caption.
    # Its output JSON keys are defined in the system prompt.
    human_prompt_blog_generation = f"""
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

Generate **up to four relevant focus keywords** in Persian based on the source title and body. Define their roles and target presence:
*   **Primary Keyword (کلمه کلیدی اصلی):** Generate **one primary focus keyword**. This is the absolute most important term, directly representing the core topic. Target density: ~1%. Provide this for the `primary_focus_keyword` key.
*   **Secondary Keyword (کلمه کلیدی ثانویه):** Generate **one secondary focus keyword**. This is the next most important related term, often targeting a key sub-topic or closely related concept. Target density: ~0.5%. Provide this for the `secondary_focus_keyword` key.
*   **Additional Keywords (کلمات کلیدی اضافی):** Generate **up to two additional focus keywords**. These should target important LSI (Latent Semantic Indexing) terms, synonyms, or related concepts that broaden the article's reach. Target density: ~0.25% each. Provide these as a list of strings for the `additional_focus_keywords` key.
*   **General:** You can mix Persian and English terms within each keyword if it represents a common search phrase or technical concept (e.g., 'راهکارهای یادگیری AI'). Total combined density should be around 1.5-2.0%, integrated naturally. **Avoid keyword stuffing.**

These keywords will be used to optimize other elements.

Title (عنوان):
*   Create a compelling Persian H1 title incorporating `primary_focus_keyword` (and `secondary_focus_keyword` if natural).
*   Keep meaning close to source. Prioritize English for major international brands (e.g., `Reddit`).
*   Enhance readability with Power Words or numbers if natural.

*   Create a compelling and relevant title in Persian for the **main blog post heading (H1)**.
*   Incorporate the `primary_focus_keyword`.
*   Try to naturally incorporate the `secondary_focus_keyword` as well, if possible without sacrificing clarity or sounding forced.
*   Try to keep the meaning very close to the original source title, translating it appropriately into natural Persian.
*   **Handling English Terms:** 
    *   Retain original English terms for technical concepts, brand names, specific jargon, or proper nouns where a direct Persian translation might lose meaning, search relevance, or accuracy. 
    *   **For major international brand names (e.g., Reddit, Google, OpenAI), prioritize using the original English name in the H1 title.** If a Persian transliteration is commonly used and aids readability, it can follow in parentheses, but the English form should be prominent (e.g., `Reddit (ردیت)` or simply `Reddit`).
    *   Alternatively, if you translate other technical terms to Persian, include the original English term in parentheses `()` immediately after the translation (e.g., `هوش مصنوعی (AI)`).
*   **Title Readability Enhancement:** 
    *   Attempt to use a **Power Word** (like "شگفت‌انگیز", "ضروری", "اثبات‌شده", "راز", "نهایی", "ساده") if it fits naturally and enhances clickability.
    *   Consider including a **number** (e.g., "7 راهکار...") if it makes sense for the content (like a list post).

# NEW: SEO Title (Rank Math)
SEO Title (عنوان سئو):

*   Generate a separate, concise title specifically optimized for **search engine results pages (SERPs)**.
*   **Strictly keep this title under 60 characters.**
*   **Crucially, the exact `primary_focus_keyword` MUST be included prominently, ideally starting the SEO title. This is a strict SEO requirement.**
*   Base it on the main Title and keywords, but prioritize brevity and SERP click-through rate.

Permalink/Slug (پیوندیکتا):

Generate a concise, SEO-friendly permalink (slug) based primarily on the `primary_focus_keyword` and source title.
Must be entirely in English. Use hyphens (-) to separate words.
Should accurately reflect the main topic and keywords.
Example: ai-learning-solutions

Meta Description (توضیح):

*   Write a compelling meta description in Persian (strictly between 150-160 characters).
*   **Crucially, the exact `primary_focus_keyword` MUST be included naturally within the description. This is a strict SEO requirement.**
*   Try to naturally incorporate the `secondary_focus_keyword` as well, if possible.
*   Accurately summarize the post's content to maximize click-through rate (CTR) from search results.
*   Include a strong call-to-action (e.g., "بیشتر بدانید") to improve CTR.

Content Generation:

*   **Introduction:** In the first paragraph, include a friendly, personal greeting addressing the Hooshews (هوشیوز) audience directly, but **do not always place it as the very first sentence**. Vary the placement and style of the greeting to keep introductions feeling natural and diverse. Write the introduction (and the whole post) in a conversational, almost journal-like tone. Connect the topic to hooshews.com's focus on AI/tech news.
*   **Focus Keyword Placement:** 
    *   **Crucially, include the exact `primary_focus_keyword` within the first 10% of the main content body (after the intro).**
    *   **Incorporate the `primary_focus_keyword` naturally into at least one `##` (H2) or `###` (H3) heading. Also incorporate the `secondary_focus_keyword` into other `##` (H2) or `###` (H3) headings where relevant.** This is important for on-page SEO.
    *   Maintain a **natural keyword density** for *all* focus keywords throughout the content, aiming for approximately 1.5-2.0% density *combined* (Primary: ~1%, Secondary: ~0.5%, Additional: ~0.25% each), integrated naturally. **Avoid keyword stuffing.**
*   **Body:** Write a comprehensive, *unique* Persian blog post that summarizes, explains, and potentially *adds value beyond* the key information from the source body. 
    *   **Strictly avoid copying sentences or significant phrases** from the source body. Focus on synthesizing information and expressing it in **completely original wording**.
    *   When instructed to **'add value beyond'** the source, this means incorporating elements like: **original analysis, unique examples relevant to the Persian audience, connections to recent local events or trends (if applicable), or a concluding thought/opinion.**
    *   **Target a minimum word count of 600 words, aiming for longer comprehensive content where appropriate.** Ensure the content is unique and is not just a rehash or direct translation.
*   **Structure & Readability:** 
    *   Structure the content beautifully using Markdown. Make it visually appealing and easy to scan. Use Markdown elements like bullet points (`* point`), numbered lists (`1. point`), bold text (`**important term**`).
    *   Use appropriate Markdown for headings (e.g., `##` for H2 headings, `###` for H3 headings).
    *   **Crucially, keep paragraphs short and focused, ideally 2-4 sentences and well under 120 words each.**
    *   Add at least one unique insight or perspective (e.g., a practical tip, a local context, or a forward-looking question). <--- This aligns with the 'add value' instruction above.
    *   **Suggest Media:** Where appropriate, insert placeholders like `[پیشنهاد تصویر: توضیح تصویر مورد نیاز در اینجا]` or `[پیشنهاد ویدیو: توضیح ویدیوی مورد نیاز در اینجا]` to guide manual media insertion later.
*   **Handling English Terms:** Within the body text, follow the same principle as for the title: keep essential English terms directly, or if translating, follow with the English term in parentheses `()` (e.g., `یادگیری ماشین (Machine Learning)`).
*   **Quote Handling & Attribution:** When including a direct quote:
    *   Format the quote distinctly using **Markdown blockquote syntax (prefix each line of the quote with '> ')**. You may optionally also use Persian quotation marks `« »` within the blockquoted text if appropriate for style.
    *   **Crucially, provide clear attribution.** Identify the speaker/author and their relevant title or role.
    *   Specify the context: where or when the quote originated (e.g., a specific event, publication, year).
    *   If a reliable online source for the quote exists (e.g., an official transcript, article, or interview), attempt to find and include a Markdown link `[منبع نقل قول](URL)` immediately after the attribution.
    *   Attribute using an em dash (`—`) before the source information on a new line below the quote (this should also be part of the blockquote if it directly follows the quoted text).
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

Thumbnail Image:

*   Alt Text (متن جایگزین): Provide descriptive Persian alt text for the thumbnail image. **Crucially, include the exact `primary_focus_keyword` naturally within the alt text.** Try to include the `secondary_focus_keyword` as well if natural. Incorporate other relevant keywords (from the source title and body) for image SEO.
*   Filename: The English `slug` generated will be used to create the filename `hooshews.com-[slug].webp` later.

Tags:

# MODIFIED: Ask for specific English AND general Persian tags
Suggest a total of **up to 7 tags** based on the source title and body, chosen for SEO value and relevance:
*   **3 English Tags:** Focus on **specific entities, technical terms, or proper nouns** (e.g., "Google Gemini", "OpenAI", "LLM", "API"). Avoid general conceptual English tags.
*   **4 Persian Tags:** Focus on **general but highly relevant SEO keywords** related to the topic (e.g., "هوش مصنوعی", "امنیت آنلاین", "گوگل", "فناوری").
"""

    messages = [
        SystemMessage(content=system_prompt_blog_generation),
        HumanMessage(content=human_prompt_blog_generation)
    ]
    blog_package_content = {} # This will hold the blog content, meta, tags
    blog_llm_raw_output = None
    processed_output = None 
    # Define placeholder for image prompts in case of errors later
    blog_thumbnail_image_prompt = "Error: Default blog image prompt."
    instagram_post_image_prompt = "Error: Default Instagram image prompt."
    pantry_api_id = os.getenv("PANTRY_ID") # Get Pantry ID from environment


    try:
        logging.info(f"Invoking LLM for Blog Content Generation (Source: {source_name}, Title: {source_title[:50]}...).)")
        response = await llm_blog_client.ainvoke(messages)
        blog_llm_raw_output = response.content 
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
                    error=f"Blog content JSON missing keys: {missing_keys}", 
                    slug='json-error-blog',
                    pantry_id=pantry_api_id # Pass pantry_id
                )
                return {"error": f"Blog content LLM response missing keys: {missing_keys}"}
            
            if not isinstance(blog_package_content.get('additional_focus_keywords'), list):
                logging.error(f"Invalid type for 'additional_focus_keywords': expected list")
                await save_output_to_file_async(
                    raw_blog_output=processed_output, 
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
            logging.error(f"Failed to decode JSON from Blog LLM: {json_err}. Raw: {processed_output}")
            await save_output_to_file_async(
                raw_blog_output=processed_output, 
                error=str(json_err), 
                slug='json-decode-error-blog',
                pantry_id=pantry_api_id # Pass pantry_id
            )
            return {"error": f"Could not parse Blog LLM response as JSON. See logs."}
        
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

                instagram_post_image_prompt = await generate_instagram_image_prompt( # For Instagram post image
                    llm_client=llm_image_prompt_client,
                    header=source_title, # Can also use source_title for context here
                    description=source_body # Or specific snippets if preferred later
                )
                final_package['instagram_image_prompt'] = instagram_post_image_prompt
            else:
                final_package['image_prompt'] = "Error: Missing source for blog image prompt."
                final_package['instagram_image_prompt'] = "Error: Missing source for Instagram image prompt."
                logging.warning("Missing source_title or source_body for image prompt generation.")
        else:
            final_package['image_prompt'] = "Error: Blog image prompt LLM client not available."
            final_package['instagram_image_prompt'] = "Error: Instagram image prompt LLM client not available."
            logging.error("Skipping image prompt generation; llm_image_prompt_client was None.")
        
        # --- Conditionally Generate Instagram Texts ---
        # Only run this section if include_instagram_texts is True
        if include_instagram_texts:
            try:
                logging.info("Starting Instagram text analysis and generation...")
                # Step 1: Analyze blog content to derive inputs for Instagram texts
                derived_insta_inputs = await analyze_blog_for_instagram_inputs(
                    llm_client=llm_instagram_text_client, 
                    blog_title=blog_package_content.get('title'),
                    blog_content=blog_package_content.get('content')
                )

                if derived_insta_inputs.get("error"):
                    logging.error(f"Error during Instagram blog analysis: {derived_insta_inputs.get('error')}")
                    # Optionally set error in result_package if needed
                else:
                    logging.info("Blog analysis for Instagram complete.")
                    
                    # Step 2: Generate Instagram title and caption using derived inputs
                    insta_texts = await generate_instagram_post_texts(
                        llm_client=llm_instagram_text_client, 
                        derived_blog_topic=derived_insta_inputs.get("derived_blog_topic"),
                        derived_key_takeaways=derived_insta_inputs.get("derived_key_takeaways"),
                        derived_cta_word=derived_insta_inputs.get("derived_cta_word"),
                        derived_core_emotion=derived_insta_inputs.get("derived_core_emotion")
                    )
                    
                    if insta_texts.get("error"):
                        logging.error(f"Error during Instagram text generation: {insta_texts.get('error')}")
                        # Optionally set error in result_package
                    else:
                        logging.info("Instagram text generation complete.")
                        # Add generated Instagram texts to the main result package
                        blog_package_content['instagram_post_title'] = insta_texts.get('instagram_post_title')
                        blog_package_content['instagram_post_caption'] = insta_texts.get('instagram_post_caption')

            except Exception as insta_gen_e:
                logging.exception(f"An unexpected error occurred during Instagram text generation: {insta_gen_e}")
                # Optionally set a general error in result_package

        # --- Conditionally Generate Instagram Story Teasers ---
        # Only run this section if include_story_teasers is True and LLM client is available and blog content is available
        if include_story_teasers and llm_instagram_text_client and blog_package_content.get('content'):
            try:
                logging.info("Starting Instagram Story teaser generation...")
                story_teasers_result = await generate_instagram_story_teasers(
                    llm_client=llm_instagram_text_client,
                    blog_content=blog_package_content.get('content') # Use the generated blog content
                )
                # Add story teasers to the final package
                final_package['instagram_story_teasers'] = story_teasers_result
                logging.info("Instagram Story teaser generation complete.")

            except Exception as insta_story_gen_e:
                logging.exception(f"An unexpected error occurred during Instagram Story teaser generation: {insta_story_gen_e}")
                # Optionally set a general error in final_package for story teasers
                final_package['instagram_story_teasers'] = {"error": f"Error generating Instagram Story teasers: {insta_story_gen_e}"}

        elif not include_story_teasers:
             logging.info("Instagram Story teaser generation skipped by user.")
        elif not llm_instagram_text_client:
             logging.warning("Skipping Instagram Story teaser generation; llm_instagram_text_client was None.")
             final_package['instagram_story_teasers'] = {"error": "Instagram text LLM client not available for story teasers."}
        elif not blog_package_content.get('content'):
             logging.warning("Skipping Instagram Story teaser generation; blog content not available.")
             final_package['instagram_story_teasers'] = {"error": "Blog content not available for story teasers."}

        await save_output_to_file_async(
            raw_blog_output=blog_llm_raw_output,
            raw_image_prompt=blog_thumbnail_image_prompt, # Use the initialized variable
            raw_instagram_post_image_prompt=instagram_post_image_prompt, # Use the initialized variable
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
            raw_instagram_post_image_prompt=instagram_post_image_prompt,
            error=str(e), 
            slug='error-blog-pkg',
            pantry_id=pantry_api_id_error # Pass pantry_id
        ) 
        return {"error": f"Error generating Persian blog package: {e}"}


# --- Image Prompt Generation Function ---
async def generate_image_prompt(llm_client: ChatOpenAI, header: str, description: str) -> str:
    """ Docstring for generate_image_prompt """
    prompt_fstring = f"""
Image Prompt for Blog Post Thumbnail:

Generate a single, creative prompt for an AI news blog post thumbnail:
- Start with: `Create image for a blog post thumbnail.`
- Visualize the core theme of the `[HEADER]` and `[DESCRIPTION]` in a style that's vibrant, modern, and eye-catching.
- Subtly include the provided character's likeness as a minor, natural part of the scene (not the main focus, not pasted in, but blended in contextually—like an easter egg).
- Use the Hooshews brand color `#4379f2` only as a small accent (never as the main theme or background).
- Add a subtle reference to "Hooshews" if possible.
- Ensure the image is unique, high-CTR, and suitable for a 16:9 thumbnail.
- **Respond only with the generated image prompt.**

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

# --- Instagram Image Prompt Generation Function ---
async def generate_instagram_image_prompt(llm_client: ChatOpenAI, header: str, description: str) -> str:
    """Generate a professional, satirical, witty, and visually bold image prompt for an Instagram post about tech/AI."""
    prompt_fstring = f"""
Instagram Image Prompt for Viral Post:

Generate a single, creative prompt for an Instagram post image:

- Start with: `Create image for an Instagram post.`
- Visualize a bold, satirical, and visually striking scene inspired by the [HEADER] and [DESCRIPTION], playfully poking fun at the tech/AI world, its trends, or personalities.
- The image should be eye-catching, unordinary, a little bit naughty and abnormal, but always highly relevant to the topic and suitable for a tech/AI news post.
- Use clever exaggeration, industry in-jokes, or surreal elements to create a sense of "AI culture satire"—not childish or slapstick.
- Humor should be smart, topical, and a bit irreverent, but always feel professional and on-brand for a tech-savvy audience.
- Use the Hooshews brand color #4379f2 as a small accent only.
- Subtly include the provided character in a witty or mischievous way, as a "signature" or easter egg.
- Ensure the image is unique, highly shareable, and suitable for a square Instagram post.
- **Respond only with the generated image prompt.**

---

**`[HEADER]`**: {header}
**`[DESCRIPTION]`**: {description}
---
    """
    messages = [HumanMessage(content=prompt_fstring)]
    try:
        logging.info(f"Invoking Instagram Image Prompt LLM (async)...")
        response = await llm_client.ainvoke(messages)
        logging.info("Instagram Image Prompt LLM invocation successful (async).")
        return response.content.strip()
    except Exception as e:
        logging.exception(f"Error during async Instagram Image Prompt LLM invocation: {e}")
        return f"Error generating Instagram image prompt: {e}"

# --- New Instagram Post Text Generation Function (Using Specific Template) ---
async def generate_instagram_post_texts(llm_client: ChatOpenAI, derived_blog_topic: str, derived_key_takeaways: list[str], derived_cta_word: str, derived_core_emotion: str) -> dict:
    """Generates Instagram Viral Post Title and Engaging Caption using AI-derived inputs and a detailed template."""
    
    takeaways_formatted = "\n".join([f"    * {point}" for point in derived_key_takeaways])

    # --- System Prompt for Instagram Text Generation ---
    system_prompt_instagram_texts = f"""
**Objective:** Generate an Instagram main post (Viral Title + Engaging Caption) for the AI news blog, "hooshews," to drive engagement and traffic to the full blog post.

**Your Role:** You are an expert AI-powered Instagram content strategist for "hooshews." Your mission is to craft compelling content that not only grabs attention but also connects with our tech and AI community on a deeper level, making them feel part of the hooshews conversation. 

**Tone:** Your tone should be professional, engaging, and approachable. Maintain a tone that reflects expertise and trustworthiness, while still being interesting and inviting for the "hooshews" AI community. Avoid overly casual, slangy, or attention-seeking language. Humor, if used, should be subtle, intelligent, and witty, aligning with a tech-savvy audience. Where appropriate, weave in concise storytelling elements or a narrative approach to make the information more compelling and relatable, drawing the audience into the core message.

**Output Instructions:**
Provide the output as a single JSON object with two keys: "instagram_post_title" and "instagram_post_caption".
Example: {{"instagram_post_title": "[Generated Title]", "instagram_post_caption": "[Generated Caption]"}}
Ensure the generated text is entirely in Persian. Adhere strictly to the formatting guidelines for the caption provided in the user prompt.
    """

    # --- Human Prompt for Instagram Text Generation (Task-Specific) ---
    human_prompt_instagram_texts = f"""
**Please provide the following two pieces of text based on the blog post details I provide below:**

**Blog Post Details (AI-Derived):**
* **Blog Post Topic/Main Subject:** {derived_blog_topic}
* **Key Takeaways/Summary of Blog Post (3-5 bullet points):**
{takeaways_formatted}
* **Specific Call-to-Action Word (for comments):** {derived_cta_word}
* **Core Emotion/Reaction you want to evoke with the post:** {derived_core_emotion}

---

**1. Viral Post Title (for the post's visual/thumbnail):**

* **Language:** Persian
* **Length:** Super short (ideally 3-7 words).
* **Style:** Explosively viral. Make it bold, playful, and a bit "naughty" or highly provocative in a clever way (think intriguing double meanings, not offensive). It must spark immediate curiosity or amazement and make people *need* to know more.
* **Hook:** Should be an irresistible hook that makes people stop scrolling.
* **Wordplay:** Use clever wordplay, a surprising twist, or a challenging statement if possible.
* **Impact:** Aim for something that makes people laugh, blush slightly, feel mischievous, or be utterly amazed.
* **Emojis:** Add 1-2 relevant emojis that enhance the title's vibe.

---

**2. Instagram Post Caption (Stylized for Readability & Engagement):**

* **Language:** Persian
* **Overall Style:** Highly readable, engaging, and visually broken up for Instagram. Think short, punchy lines and mini-paragraphs. Use emojis strategically for emphasis and visual appeal.
* **Tone (Reiteration for Emphasis):** Professional, engaging, and approachable. Maintain a tone that reflects expertise and trustworthiness, while still being interesting and inviting for the "hooshews" AI community. Avoid overly casual, slangy, or attention-seeking language. Humor, if used, should be subtle, intelligent, and witty, aligning with a tech-savvy audience.

* **Structure & Formatting Guidelines:**
    *   **Short Lines:** Keep most lines relatively short. Use single newlines (`\n`) frequently to create visual breaks and improve scannability.
    *   **Mini-Paragraphs/Stanzas:** Group related sentences into small blocks of 1-3 lines, separated by a single newline.
    *   **Strategic Emojis:**
        *   Use emojis sparingly and purposefully. They should only be used if they genuinely enhance the message or visual appeal, not as mere decoration. Aim for a maximum of 1-2 well-placed emojis in the entire caption, if any. The strength of the caption should come from compelling copy, not emoji overuse.
    *   **Hook:** Start with a strong, intriguing hook (can be a question or a bold statement).
    *   **Summary:** Briefly summarize the core topic (using the AI-Derived Key Takeaways) in an exciting, digestible way, broken into these short, stylized lines.
    *   **Engagement Questions:** Weave in 1-2 thought-provoking questions, each perhaps on its own line or as a short stanza.
    *   **Call-to-Action (CTA):**
        *   Make the CTA very clear and visually distinct. It could be its own stanza.
        *   Instruct users to comment with **{derived_cta_word}** to receive the full blog link in their DMs.
        *   Mention the link in the "hooshews" page bio.
    *   **Hashtags:**
        *   Place all hashtags at the very end of the caption, on their own line(s) after any other text.
        *   Provide exactly 5 hashtags: 3 highly relevant Persian and 2 highly relevant English, each starting with '#'.
        *   **Selection Strategy:** These hashtags are crucial for increasing visibility, maximizing reach, and enhancing discoverability. Aim for a strategic mix:
            *   Include some **popular/broader** Persian hashtags for wider reach.
            *   Include some **niche-specific** Persian and English hashtags directly related to the post's core AI/tech topic for targeted engagement.
            *   Consider using a **branded hashtag** like #hooshews or #هوشیوز as one of the English or Persian tags if it fits naturally within the count.
            *   If relevant and suitable for the content, try to align one or two hashtags with **trending topics** in the AI/tech space (but prioritize relevance over chasing trends).
        *   Ensure hashtags are space-separated if on the same line, or on new lines.

* **Example Snippet of Desired Formatting (Illustrative - ADAPT THE STRUCTURE AND EMOJI PLACEMENT TO THE ACTUAL CONTENT, but follow this visual style closely. Note the reduced emoji usage in this example):**
    می‌گن تو iOS 19، هوش مصنوعی قراره با باتری آیفون... همکاری کنه؟

    شایعه‌ جدید در دنیای اپل:
    اپل ممکنه در iOS 19 از AI برای بهینه‌سازی عمر باتری آیفون استفاده کنه.

    این هوش مصنوعی یاد می‌گیره چطور از گوشی‌تون استفاده می‌کنید و بر اساس اون، مصرف باتری رو هوشمندانه مدیریت می‌کنه.
    این خبر از منابع معتبری مثل بلومبرگ منتشر شده و به نظر می‌رسه با Apple Intelligence در ارتباط باشه. 🤖

    اما سوال اصلی اینه:
    آیا این یک پیشرفت واقعی در هوش مصنوعیه یا صرفاً یک نام جذاب برای یک آپدیت دیگر؟
    و چقدر می‌تونیم به این سیستم AI اعتماد کنیم؟

    📩 برای اطلاع از جزئیات کامل این خبر:
    زیر همین پست کامنت کنید **{derived_cta_word}** تا لینک کامل مطلب براتون ارسال بشه.
    لینک مستقیم در بیو پیج هم موجوده.

    #تگ_فارسی_نمونه #مثال_دیگر #سومین_تگ #SampleEnglishTag #AnotherExample
    """
    messages = [
        SystemMessage(content=system_prompt_instagram_texts),
        HumanMessage(content=human_prompt_instagram_texts)
    ]
    instagram_texts = {}
    try:
        logging.info(f"Invoking LLM for Instagram Post Texts (Derived Topic: {derived_blog_topic[:50]}...)...")
        response = await llm_client.ainvoke(messages)
        raw_output = response.content.strip()
        logging.info("LLM invocation for Instagram Post Texts successful.")
        
        # Clean potential markdown fences
        cleaned_output = raw_output.strip()
        if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output[7:]
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3]
        cleaned_output = cleaned_output.strip()

        try:
            # Attempt 1: More careful aggressive cleaning for common LLM JSON issues.
            # Goal: transform internal newlines in strings to \\n, fix common structural issues.
            
            # Step 1: Protect already correctly escaped sequences
            temp_output = cleaned_output.replace('\\"', '__TEMP_QUOTE__') # Protect escaped quotes
            temp_output = temp_output.replace('\\n', '__TEMP_NEWLINE__') # Protect escaped newlines
            
            # Step 2: Convert problematic literal newlines within presumed string content to __TEMP_NEWLINE__
            # This is heuristic: find newlines that are likely inside quotes.
            # This regex finds "key": "value\nvalue" and replaces \n with __TEMP_NEWLINE__
            # It's hard to make perfect, but aims for common cases.
            # A simpler approach might be to just replace all remaining \n with \n, then fix structural ones.
            # For now, let's be more direct: assume all remaining newlines *inside typical string content* should be escaped.
            # This is risky if newlines are part of the JSON structure and not properly handled by LLM.
            # A simpler, broad replacement:
            temp_output = temp_output.replace('\n', '__TEMP_NEWLINE__')
            
            # Step 3: Restore protected sequences
            temp_output = temp_output.replace('__TEMP_NEWLINE__', '\\n') # Convert to proper JSON newline escape
            temp_output = temp_output.replace('__TEMP_QUOTE__', '\\"')
            temp_output = temp_output.replace('__TEMP_BACKSLASH__', '\\')
            
            # Step 4: Remove trailing commas before closing braces/brackets
            temp_output = re.sub(r',[\s]*(\}|\])', r'\1', temp_output)
            
            parsed_json = json.loads(temp_output)
            if isinstance(parsed_json, dict) and \
               "instagram_post_title" in parsed_json and \
               "instagram_post_caption" in parsed_json:
                instagram_texts = parsed_json
                # Unescape \\n to \n for display/use if they were part of original string values
                if isinstance(instagram_texts.get("instagram_post_title"), str):
                    instagram_texts["instagram_post_title"] = instagram_texts["instagram_post_title"].replace('\\n', '\n')
                if isinstance(instagram_texts.get("instagram_post_caption"), str):
                    instagram_texts["instagram_post_caption"] = instagram_texts["instagram_post_caption"].replace('\\n', '\n')
                logging.info("Successfully parsed JSON for Instagram texts after cleaning attempts.")
            else:
                logging.warning("Parsed JSON after cleaning, but required keys missing.")
                raise json.JSONDecodeError("Missing keys after cleaning", temp_output, 0)
        
        except json.JSONDecodeError as json_err_cleaned:
            logging.warning(f"JSON parsing failed after cleaning attempts ({json_err_cleaned}). Falling back to regex on original cleaned_output.")
            
            # Regex fallback on the state of cleaned_output *before* aggressive in-string newline replacement
            title_match = re.search(r'"instagram_post_title"\\s*:\\s*"(.*?)"(?=\\s*,\\s*"instagram_post_caption"|\s*\\})', cleaned_output, re.DOTALL)
            caption_match = re.search(r'"instagram_post_caption"\\s*:\\s*"(.*?)"(?=\\s*\\})', cleaned_output, re.DOTALL)

            if title_match and caption_match:
                title_str = title_match.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
                caption_str = caption_match.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
                
                instagram_texts = {
                    "instagram_post_title": title_str,
                    "instagram_post_caption": caption_str
                }
                logging.info("Successfully extracted Instagram texts using regex fallback.")
            else:
                logging.error(f"Could not parse Instagram texts with regex fallback. Title match: {bool(title_match)}, Caption match: {bool(caption_match)}. Raw: {cleaned_output}")
                instagram_texts = {"error": "Could not parse Instagram texts from LLM (regex fallback failed)."}

    except Exception as e:
        logging.exception(f"Error during Instagram Post Text generation: {e}")
        instagram_texts = {"error": f"Error generating Instagram texts: {e}"}
    
    # Safely modify the caption if it exists and is a string, and no error occurred
    if "error" not in instagram_texts and \
       "instagram_post_caption" in instagram_texts and \
       isinstance(instagram_texts.get("instagram_post_caption"), str):
        
        caption = instagram_texts["instagram_post_caption"]
        # Replace sequences of two or more newlines with a single newline
        modified_caption = re.sub(r'\n{2,}', '\n', caption)
        
        if caption != modified_caption: # Log only if a change was made
            instagram_texts["instagram_post_caption"] = modified_caption
            logging.info("Normalized multiple newlines in Instagram caption to single newlines (e.g., \\n\\n -> \\n).")
            
    return instagram_texts

# --- New Function to Analyze Blog Content for Instagram Inputs ---
async def analyze_blog_for_instagram_inputs(llm_client: ChatOpenAI, blog_title: str, blog_content: str) -> dict:
    """Analyzes generated blog title and content to derive inputs for Instagram text generation."""
    
    # --- System Prompt for Blog Analysis for Instagram ---
    system_prompt_analyze_blog = f"""
Objective: Analyze the provided Blog Post Title and Content to extract key information needed to generate a viral Instagram post for the AI news blog "hooshews".

Your Role: You are an expert AI Content Analyst. Your task is to process the blog information and determine the optimal inputs for a subsequent Instagram content generation step.

Output Instructions:
Provide the following information strictly in a JSON object format, with the specified keys:
1.  `"derived_blog_topic"`: (String) The main topic or subject of the blog post. This can be the original title or a slightly rephrased, concise version if more suitable for internal processing.
2.  `"derived_key_takeaways"`: (List of strings) Extract exactly 3 to 5 of the most important, concise, and engaging key takeaways from the blog content. Each takeaway should be a short sentence or phrase.
3.  `"derived_core_emotion"`: (String) Identify and state the single most dominant and effective core emotion (e.g., Amazement, Concern, Curiosity, Excitement, Intrigue, Urgency, Humor) that an Instagram post about this blog content should aim to evoke in the "hooshews" audience to maximize engagement.
4.  `"derived_cta_word"`: (String) Suggest a single, highly effective Persian call-to-action word (e.g., "جزئیات", "بیشتر", "لینک", "مقاله", "کاملشو_ببین", "تحلیل") that users should comment to receive the blog link. The word should be catchy and relevant to the topic and desired emotion.

Provide ONLY the JSON object in your response.
"""

    # --- Human Prompt for Blog Analysis for Instagram (Task-Specific) ---
    human_prompt_analyze_blog = f"""
Blog Post Title: {blog_title}

Blog Post Content (Markdown):
{blog_content}

---

Based on the Blog Post Title and Content above, provide the information as specified in the system prompt (JSON format with keys: derived_blog_topic, derived_key_takeaways, derived_core_emotion, derived_cta_word).

Example JSON Output (for clarity on expected values and structure):
{{
  "derived_blog_topic": "AI's New Stock Market Prediction Power",
  "derived_key_takeaways": [
    "New AI analyzes vast data to predict market crashes with high accuracy.",
    "Showed 90% accuracy in back-testing historical crashes.",
    "Raises questions about market stability and ethical control of such power."
  ],
  "derived_core_emotion": "Amazement",
  "derived_cta_word": "تحلیل"
}}
"""

    messages = [
        SystemMessage(content=system_prompt_analyze_blog),
        HumanMessage(content=human_prompt_analyze_blog)
    ]
    derived_inputs = {}
    try:
        logging.info(f"Invoking LLM for Blog Analysis for Instagram Inputs (Title: {blog_title[:50]}...)...")
        response = await llm_client.ainvoke(messages)
        raw_output = response.content.strip()
        logging.info("LLM invocation for Blog Analysis successful.")
        
        # Clean potential markdown fences
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip() # Clean any leading/trailing whitespace again

        try:
            parsed_json = json.loads(raw_output)
            required_keys = ["derived_blog_topic", "derived_key_takeaways", "derived_core_emotion", "derived_cta_word"]
            if isinstance(parsed_json, dict) and all(key in parsed_json for key in required_keys):
                # Further validation for key_takeaways being a list
                if not isinstance(parsed_json.get("derived_key_takeaways"), list):
                    logging.error(f"Invalid type for 'derived_key_takeaways': expected list, got {type(parsed_json.get('derived_key_takeaways'))}. Output: {raw_output}")
                    derived_inputs = {"error": "Derived key takeaways is not a list."}
                else:
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
        derived_inputs = {"error": f"Error during Blog Analysis: {e}"}
    
    return derived_inputs

# --- Function to Generate Instagram Story Teasers (3-Component Version) ---
async def generate_instagram_story_teasers(
    llm_client: ChatOpenAI,
    blog_content: str
) -> dict:
    """
    Generates three Farsi teaser snippets for an Instagram Story based on the blog content.
    Uses a specific 3-component prompt structure.
    """
    logging.info("Starting Instagram Story Teaser generation...")

    # --- System Prompt for Instagram Story Teasers (3-Component - CORRECTED) ---
    system_prompt_story = """You are an AI assistant embodying the persona of an **elite Farsi copywriter, a master storyteller, and a subtle movement builder**. Your mission is to craft exceptionally compelling and concise Farsi-language snippets for a social media story. These snippets are teasers for the provided blog post. Your primary objectives are to:
1.  Instantly seize attention and spark immediate engagement.
2.  Generate deep curiosity and a palpable sense of urgency.
3.  Make the audience feel profoundly understood, as if this content is crafted *specifically for their current challenges and aspirations*.
4.  Position the blog post as a valuable **'new opportunity,'** the key to a critical **'epiphany,'** or the crucial information that overcomes a significant hurdle.
5.  Create an undeniable belief that the blog post holds essential insights, compelling them to click through and read the full article.
6.  Subtly address and begin to dismantle potential skepticism or common **'false beliefs'** the audience might hold regarding the topic.

**Instructions:**
Based *only* on the content of the blog post (provided in the human prompt), generate the following **three Farsi components**. You will subtly adapt advanced principles from expert copywriting and storytelling (including AIDA, PAS, creating belief, the 'Big Domino,' 'Epiphany Bridge,' the 'Hero's Two Journeys' concept of transformation, and addressing 'False Belief Patterns') to maximize impact for *very short-form content*. The "Hooshews" brand, in this context, acts as a trusted **'Reporter/Relater'** and a guiding voice, bringing these insights to the forefront.

1.  **Main Title (The Hook & Dramatic Entry):**
    *   Start **'in medias res'** – with the most dramatic, attention-grabbing, or urgent aspect of the blog post, creating an immediate emotional connection or question.
    *   This is your **bold opening (AIDA: Attention)**. It should function like a "big promise" combined with "massive curiosity," hinting at a core problem, desire, or a surprising revelation.

2.  **Subtitle/Question (Spark Interest, Introduce Conflict/Cause & Agitate):**
    *   Build intense **interest (AIDA)** by posing a critical question or highlighting a significant challenge/conflict the blog post directly addresses.
    *   Subtly frame this within a larger **'cause'** or struggle that is deeply relevant to the audience (e.g., the quest for unrestricted access, the pursuit of knowledge, overcoming a pervasive frustration).
    *   This is where you begin to **agitate (PAS: Agitate)** the problem, making the audience feel its weight and the need for a resolution.

3.  **Body Text (Build Desire, Hint at Epiphany/New Opportunity, Point to Solution/Big Domino, Overcome Doubt & Drive Action with Open Loops):**
    *   This combined section must first intensify **desire (AIDA)** for the information within the blog. Make the audience feel that the blog post contains a crucial insight, a **'new opportunity,'** or the key to an **'epiphany'** that can change their perspective or situation. Strongly hint at the **transformation** the blog's information offers.
    *   Then, clearly position the blog post as the **solution (PAS: Solution)** or the place where the 'epiphany' is fully unveiled and the 'new opportunity' is detailed. Frame the blog's core message as the **'Big Domino'**: the one pivotal understanding that resolves key issues.
    *   Subtly counter a potential **'false belief'** or common doubt.
    *   The implicit **Call to Action (AIDA: Action)** is to read the blog. Conclude this section with questions or statements that create compelling **'open loops,'** making it irresistible to click and discover the answers. What crucial advantage or information will they miss if they don't engage *now*?

**Overall Tone and Style:**
*   **Professional Authority, Storyteller's Heart:** Combine unimpeachable expertise with engaging, warm, and relatable storytelling that feels personal.
*   **Deeply Empathetic & Resonant:** Connect directly with the Iranian audience's implied needs, current tech-related desires (e.g., for AI accessibility, cutting-edge information), and potential frustrations (their 'pain points' and aspirations for 'pleasure'/empowerment through knowledge).
*   **Urgent yet Hopeful & Empowering:** Convey the timeliness and importance of the information, while offering the blog post as a source of valuable insight, hope, and a clear path forward.
*   **Authentically Farsi:** The language must be fluent, natural, and possess cultural depth and resonance.
*   **Concise Power & Impact:** Every word is chosen for maximum strategic impact. No filler.

Think of these snippets as the captivating opening scenes of a mini-story that the audience feels compelled to complete by reading the blog post. Your goal is to make NOT reading the blog feel like a missed opportunity for significant insight or advantage.

The output MUST be a JSON object with EXACTLY these three keys: "story_main_title", "story_subtitle", "story_body_text".
Do NOT include any other text or formatting outside the JSON object. Example:
{
  "story_main_title": "تیتر اصلی اینجا",
  "story_subtitle": "زیرنویس یا سوال اینجا",
  "story_body_text": "متن بدنه اینجا، که شامل جزئیات بیشتر و سوالات باز است."
}
"""

    # --- Human Prompt for Instagram Story Teasers (3-Component) ---
    human_prompt_story = f"""**Subject:** Generate Expert Farsi Social Media Teasers for Blog Post (3-Part Format)

**Instructions for AI (Hooshews Voice - Expert Storyteller):**

Please create a set of **three** captivating Farsi-language snippets for a social media story, based on the blog post text provided below, matching our visual template.

These snippets should act as powerful, concise teasers that:
*   Immediately grab our audience's attention.
*   Spark intense curiosity about the blog's core message.
*   Speak directly to their challenges and aspirations, making them feel the content is essential for them.
*   Make them eager to click through and discover the solutions and insights in the full article.

The desired output format is a JSON object with these keys:
1.  `"story_main_title"`
2.  `"story_subtitle"`
3.  `"story_body_text"` (This should lead in, build desire, and end with compelling questions/details that make users want to read more)

Adopt the expert 'Hooshews' voice: authoritative, deeply empathetic, and a master storyteller who understands the Iranian tech/AI audience.

**Blog Post Text:**
```
{blog_content}
```
"""
    messages = [
        SystemMessage(content=system_prompt_story),
        HumanMessage(content=human_prompt_story)
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
        response = await llm_client.ainvoke(messages)
        raw_output = response.content
        story_teasers["raw_output"] = raw_output
        logging.info(f"LLM for Instagram Story Teasers successful. Raw output: {raw_output[:200]}...")

        # Attempt to parse the JSON response
        try:
            # Clean potential markdown fences around JSON
            cleaned_output = raw_output.strip()
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output[7:]
            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3]
            cleaned_output = cleaned_output.strip()

            parsed_json = json.loads(cleaned_output)
            story_teasers["story_main_title"] = parsed_json.get("story_main_title", "Error: Missing main title")
            story_teasers["story_subtitle"] = parsed_json.get("story_subtitle", "Error: Missing subtitle")
            story_teasers["story_body_text"] = parsed_json.get("story_body_text", "Error: Missing body text")
            if not (parsed_json.get("story_main_title") and parsed_json.get("story_subtitle") and parsed_json.get("story_body_text")):
                story_teasers["error"] = "One or more required fields missing in story teaser JSON."
                logging.error(f"Story Teaser JSON missing fields. Parsed: {parsed_json}")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from Story Teaser LLM: {e}. Raw: {raw_output}")
            story_teasers["error"] = f"Could not parse Story Teaser LLM response as JSON: {e}"
            # Fallback: Try to extract fields using regex if JSON parsing fails
            title_match = re.search(r'"story_main_title":\\s*"(.*?)"', raw_output, re.DOTALL)
            subtitle_match = re.search(r'"story_subtitle":\\s*"(.*?)"', raw_output, re.DOTALL)
            body_match = re.search(r'"story_body_text":\\s*"(.*?)"', raw_output, re.DOTALL)

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
                 # Preserve the original JSON decode error, but add to it
                 current_error = story_teasers.get("error", "")
                 story_teasers["error"] = f"{current_error} | Regex extraction also failed or incomplete.".strip(" | ")
            else:
                logging.info("Successfully extracted story teaser fields using fallback regex.")
                story_teasers["error"] = None # Clear JSON error if regex was successful

    except Exception as e:
        logging.exception("An unexpected error occurred during Instagram Story Teaser generation.")
        story_teasers["error"] = f"Unexpected error in story teaser generation: {e}"
        story_teasers["story_main_title"] = "Error: Generation failed"
        story_teasers["story_subtitle"] = "Error: Generation failed"
        story_teasers["story_body_text"] = "Error: Generation failed"

    return story_teasers
# --- END OF Instagram Story Teaser Function ---

# Utility function to save raw LLM output and any errors to a file
# (Assuming save_output_to_file is defined elsewhere, e.g., in file_utils.py)
# def save_output_to_file(raw_blog_output=None, raw_ig_output=None, raw_story_output=None, error=None, slug='error_log'):
#    # ... implementation details ...
#    pass 