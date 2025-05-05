# 📄 PersiaPress AI

Automate your WordPress workflow: Generate Persian blog posts from English sources using AI and publish drafts instantly.

Welcome to the **PersiaPress AI** repository! Based on the codebase analysis, this project appears to implement a Streamlit-based web application designed to streamline the process of creating Persian blog content for a WordPress website (`hooshews.com`) from English source material, leveraging Large Language Models (LLMs).

The application consists of the following core components:
- **Streamlit UI (`app/ui.py`, `app/app.py`):** Provides the web interface for user input (source article details, image upload) and output display.
- **Utility Functions (`app/utils.py`):** Contains the logic for interacting with LLMs (via Langchain/OpenAI compatible API) to generate content packages and interacting with the WordPress REST API to create posts and upload media.
- **Configuration (`dotenv`):** Manages sensitive information like API keys and WordPress credentials.

This tool aims to automate the translation, SEO optimization, and initial drafting process for blog posts, taking an English article and producing a ready-to-review Persian draft in WordPress, complete with potential tags and a featured image.

---

## ✨ Overview

This project provides a web interface built with Streamlit that takes details of an English source article (title, body, source name, URL). It then uses configured LLM clients (specifically interacting with an OpenAI-compatible API, potentially via `langchain-openai`) to generate a comprehensive Persian blog post package. This package includes not only the translated and SEO-optimized content (Markdown format) but also metadata like a title, English slug, meta description, image alt text, suggested tags (English and Persian), focus keywords, and even Instagram teasers. Finally, it interacts with a WordPress site's REST API to automatically create a draft post, including converting Markdown content to HTML, attempting to resolve/create tags, uploading a provided thumbnail image as the featured media, and attempting to set Rank Math SEO fields via a custom endpoint.

Based on the analysis, key features appear to include:

*   **LLM-Powered Content Generation:** Utilizes LLMs to generate a full Persian blog package (title, slug, content, metadata, etc.) based on English input and detailed prompts focused on SEO and specific formatting.
*   **WordPress Draft Creation:** Automates the creation of draft posts via the WordPress REST API using Application Passwords for authentication.
*   **Markdown to HTML Conversion:** Automatically converts the LLM-generated Markdown content to HTML before posting to WordPress.
*   **Tag Management:** Attempts to find existing WordPress tags by name or create new *ASCII* tags via the API. Includes a default tag.
*   **Featured Image Upload:** Allows uploading a thumbnail via the UI, saves it locally (in the `images/` directory), and uploads it to the WordPress Media Library, setting it as the featured image for the created draft.
*   **Streamlit Web Interface:** Provides an easy-to-use interface for input, triggering generation, displaying results, and uploading images.
*   **Output Persistence:** Saves the raw and processed LLM outputs to JSON files in the `answers/` directory for review.
*   **(Attempted) Rank Math Integration:** Includes logic to send generated SEO title, description, and focus keywords to a custom Rank Math API endpoint, though previous attempts indicated potential unreliability.

This application serves as an automation tool to accelerate the content creation workflow for the `hooshews.com` WordPress site.

---

## 🗂️ File Structure

```
.
├── .git/             # Git version control files
├── .venv/            # Python virtual environment (ignored by Git)
├── app/              # Core application source code
│   ├── __init__.py   # Makes 'app' a Python package
│   ├── app.py        # Main Streamlit application entry point
│   ├── ui.py         # Defines the Streamlit user interface components
│   └── utils.py      # Contains helper functions (LLM interaction, WP API calls)
├── answers/          # Directory for storing LLM output JSON files (ignored by Git)
├── images/           # Directory for storing uploaded thumbnail images (ignored by Git)
├── plugins/          # Contains related plugins (e.g., for WordPress)
│   └── rank-math-api-manager-extended-v1.3.zip # Custom Rank Math API plugin
├── .gitignore        # Specifies intentionally untracked files for Git
├── .python-version   # Specifies the intended Python version (3.11)
├── hello.py          # Simple test script (likely unrelated to main app)
├── pyproject.toml    # Project metadata and dependencies (for UV / PEP 621 build systems)
├── README.md         # This file
└── uv.lock           # Lock file for dependencies managed by UV package manager
```

---

## 🚀 Features

*   **Source Input:** Accepts English source article title, body, source name, and URL via a Streamlit web form.
*   **LLM Content Package Generation:**
    *   Sends source material to an LLM (via `langchain-openai`) using a detailed prompt.
    *   Generates: Persian Title (H1), English Slug, Persian Content (Markdown), Persian Meta Description, Persian Image Alt Text, Primary/Secondary Persian Focus Keywords, SEO Title (for Rank Math), specific English Tags, general Persian Tags, Instagram Story Title & Teaser.
    *   Prompt emphasizes SEO optimization (keyword placement, density, structure), humanized tone, external linking (Markdown format), and specific output JSON format.
*   **Image Prompt Generation:** Uses a separate LLM call to generate a descriptive prompt for creating a thumbnail image, incorporating subtle branding and character likeness instructions.
*   **WordPress Post Creation Workflow:**
    1.  Authenticates using `WP_USERNAME` and `WP_APP_PASSWORD` via Basic Auth.
    2.  Converts generated Markdown content to HTML.
    3.  Processes suggested tags: searches for existing tags by name, creates new tags if they are ASCII-only (skips non-ASCII), adds a default tag (ID 46).
    4.  Creates a draft post (`POST /wp/v2/posts`) with title, HTML content, slug, status 'draft', category ID 26, and resolved tag IDs.
    5.  (If image provided and found locally) Uploads the image (`POST /wp/v2/media`) with appropriate headers (`Content-Disposition`, `Content-Type`).
    6.  (If image uploaded) Updates the uploaded media item with the generated alt text (`POST /wp/v2/media/<media_id>`).
    7.  (If image uploaded) Updates the created post to set the `featured_media` field (`POST /wp/v2/posts/<post_id>`).
    8.  Attempts to update Rank Math fields (SEO title, description, focus keywords) via a custom endpoint (`POST /rank-math-api/v1/update-meta`).
*   **Local Image Handling:**
    *   Provides a file uploader in Streamlit to select a thumbnail image.
    *   Saves the uploaded image (converted to WebP) to the local `images/` directory using the LLM-generated filename (`hooshews.com-[slug].webp`).
*   **Output Loading:** Allows uploading previously generated JSON files from the `answers/` directory to repopulate the UI and retry posting to WordPress.

---

## 📋 Requirements

1.  **Software:**
    *   Python 3.11 (as specified in `.python-version`)
    *   A tool to manage Python dependencies (`uv` is strongly recommended based on `uv.lock` and `pyproject.toml`).
    *   Access to a WordPress site (`hooshews.com`) with the REST API enabled and an Application Password generated for a user with posting capabilities.
    *   Access to an OpenAI-compatible API (specifically configured for `https://api.avalai.ir/v1`) with a valid API key.
    *   (Optional but intended) The custom Rank Math API plugin (`rank-math-api-manager-extended-v1.3.zip`) installed and activated on the WordPress site.
2.  **Dependencies:** (Managed via `pyproject.toml` and `uv.lock`)
    *   `dotenv>=0.9.9`
    *   `langchain-core>=0.3.58`
    *   `langchain-openai>=0.3.16`
    *   `markdown>=3.8`
    *   `streamlit>=1.45.0`
    *   `requests` (Implicit dependency, likely pulled in by others, but essential)
    *   `Pillow` (Implicit dependency for image handling, likely pulled in)
    *   Installation requires `uv` (`uv sync`).
3.  **Environment Setup:**
    *   Create a file named `.env` in the project root directory.
    *   Populate it with the necessary credentials:

    ```env
    # LLM Configuration
    GOOGLE_API_KEY=your_google_api_key_for_avalai # Note: Despite the name, seems used for AvalAI endpoint

    # WordPress Configuration
    WP_URL=https://your-wordpress-site.com # e.g., https://hooshews.com
    WP_USERNAME=your_wordpress_username
    WP_APP_PASSWORD=your_wordpress_application_password
    ```
    _Ensure the WordPress user has permissions to create posts, upload media, and manage tags._

---

## 💻 Installation & Launch Instructions

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/Wp-Automate-Python.git # Replace with actual URL
    cd Wp-Automate-Python
    ```
2.  **Install Dependencies**
    (Using `uv` is required based on `uv.lock`)
    ```bash
    # Ensure uv is installed (e.g., pip install uv)
    uv sync
    ```
3.  **Configure Environment**
    *   Create a `.env` file in the project root.
    *   Copy the contents from the `Environment Setup` section above into `.env`.
    *   Fill in your actual API key, WordPress URL, username, and Application Password.
4.  **[Infer Build Steps?]**
    *   No build steps seem necessary for this Python application.
5.  **[Infer Database Setup?]**
    *   No database setup is required for this application itself; it relies on the external WordPress database via the API.
6.  **Launch the Application/Script**
    *   The application is run using Streamlit, targeting the `app/app.py` entry point.
    ```bash
    streamlit run app/app.py
    ```
    *   **On Windows:** Alternatively, you can simply double-click the `run.bat` file in the project root directory. This script will automatically activate the virtual environment and start the Streamlit application.
    *   Open the provided local URL (e.g., `http://localhost:8501`) in your web browser.

---

## 📝 Usage Guide

1.  Launch the application using `streamlit run app/app.py`.
2.  Access the web interface in your browser.
3.  **Input Source:** Fill in the "Source Title", "Source Body", "Source Name", and "Source URL" fields with the details of the English article.
4.  **Generate Content:** Click the "✨ Generate Persian Blog Post Package" button. Wait for the LLMs to process and generate the output.
5.  **Review Output:** Examine the generated metadata, content, image prompt, and Instagram teasers displayed in the expander sections. Copy the content or image prompt if needed.
6.  **Upload Thumbnail:** Use the "🖼️ Upload and Save Thumbnail Image" section to upload the corresponding thumbnail image. It will be saved locally to the `images/` folder with the filename suggested in the metadata (e.g., `hooshews.com-[slug].webp`).
7.  **(Optional) Load Existing Output:** Instead of generating, you can upload a `.json` file from the `answers/` folder using the "Or Upload Existing JSON Output" section.
8.  **Create WordPress Draft:** Click the "🚀 Create Draft Post in WordPress" button.
    *   The application will check if the corresponding image file exists in the `images/` folder.
    *   It will then attempt to create the draft post, upload the image (if found), and update Rank Math fields.
    *   Monitor the output messages and logs for success or failure indicators.
9.  **Verify:** Check your WordPress admin area (`hooshews.com`) for the newly created draft post in Category 26 ("اخبار"), verify the content, tags, and featured image (if uploaded). Manually adjust Rank Math fields and add any missing non-ASCII tags if necessary.

---

## ⚙️ Technical Implementation Details

### LLM Usage (`langchain-openai`, Custom Prompts)
*   The application uses `langchain-openai`'s `ChatOpenAI` client to interact with an OpenAI-compatible API endpoint (`https://api.avalai.ir/v1`).
*   **Blog Package Generation:** A detailed prompt (`generate_persian_blog_package` in `app/utils.py`) instructs the LLM (`gemini-2.5-pro-exp-03-25`) to perform translation, SEO optimization (keyword focus, headings, density, meta description), specific formatting (Markdown, external links, source attribution), and generate various metadata fields in a strict JSON format.
*   **Image Prompt Generation:** A separate prompt (`generate_image_prompt` in `app/utils.py`) instructs a different LLM (`gpt-4.1`) to create a suitable thumbnail image prompt based on the article's header and description, including style guidance and instructions for subtle character/brand integration.
*   Error handling includes JSON parsing checks and saving raw outputs.

### WordPress Interaction (REST API, `requests`)
*   Uses the `requests` library to communicate with the WordPress REST API (`/wp-json/wp/v2/`).
*   Authentication is handled via Basic Auth using a WordPress Username and an Application Password stored in the `.env` file.
*   **Endpoints Used:**
    *   `/posts` (POST): To create the initial draft post.
    *   `/posts/<id>` (POST): To update the post (specifically for setting `featured_media`).
    *   `/tags` (GET): To search for existing tags by name.
    *   `/tags` (POST): To create new *ASCII* tags.
    *   `/media` (POST): To upload the thumbnail image file.
    *   `/media/<id>` (POST): To update the alt text of the uploaded media item.
    *   `/rank-math-api/v1/update-meta` (POST): Custom endpoint (presumably from the provided plugin) to attempt setting Rank Math fields.
*   Handles potential errors during API calls using try-except blocks and logs detailed error messages, including API responses.

### UI (`streamlit`)
*   The entire user interface is built using the `streamlit` library.
*   It uses various Streamlit widgets (`text_input`, `text_area`, `button`, `file_uploader`, `expander`, `spinner`, `info`, `warning`, `error`, `success`, `code`, `markdown`) to create an interactive experience.
*   Manages application state (`st.session_state`) to hold generated or loaded data between interactions.
*   Uses `asyncio.run` to execute the asynchronous LLM generation functions within the synchronous Streamlit flow.

### File Handling & Logging
*   Uses the `os` module for path manipulation and checking file existence.
*   Uses `dotenv` to load environment variables.
*   Uses the built-in `logging` module for logging information, warnings, and errors during execution.
*   Uses the `markdown` library to convert Markdown text to HTML.
*   Uses `Pillow` (PIL) to open, convert (to RGB if necessary), and save uploaded images as WebP format in the `images/` directory.
*   Uses `mimetypes` to guess the content type of the image file before uploading to WordPress.
*   Saves LLM outputs and metadata to timestamped JSON files in the `answers/` directory.

---

## 📈 Current Status & Future Plans

### Current Status
*   The application appears functional for its core workflow: generating content via LLM and creating a WordPress draft with title, content, basic tags, and potentially a featured image.
*   The feature to automatically set Rank Math fields via the API was attempted but deemed unreliable in previous development stages and might require manual intervention in WordPress.
*   Automatic creation of non-ASCII (e.g., Persian) tags via the API is disabled due to previously encountered errors (`400 Bad Request`), likely requiring server-side configuration changes on WordPress. These tags must be added manually.
*   Network/SSL errors were encountered during recent testing when communicating with the WordPress site, potentially related to proxy/SSL configuration on the client or server side.

### Future Enhancements
*   No explicit TODOs or future plans were identified directly within the current code comments or structure. Potential improvements could include:
    *   Resolving the network/SSL errors for more reliable WordPress communication.
    *   Investigating and fixing the Rank Math API integration or removing the attempt.
    *   Finding a solution for creating non-ASCII tags via the API (perhaps different encoding or endpoint).
    *   Adding more robust error handling and user feedback.
    *   Implementing internal linking suggestions.
    *   Adding unit or integration tests.

---

## 🙌 Acknowledgments

*   No explicit acknowledgments or credits to third-party libraries (beyond dependencies) or individuals were identified within the source code comments or docstrings.

---

## 📜 License

*   No `LICENSE` file was found in the project root.
*   The `pyproject.toml` file does not specify a license.
*   The license for this project is therefore unclear or missing.

---
