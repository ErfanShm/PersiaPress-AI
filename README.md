# 📄 PersiaPress AI

Automate your WordPress workflow: Generate Persian blog posts from English sources using AI and publish drafts instantly.

## 🌟 Project Overview

The PersiaPress AI project is a Streamlit-based web application designed to automate and streamline the creation of Persian blog content for WordPress from English source material.

**Main Purpose & Problem Solved:**
The primary goal of PersiaPress AI is to simplify and accelerate the process of generating engaging Persian blog posts for the `hooshews.com` WordPress site. It addresses the challenge of manually translating, adapting, and optimizing content for a Persian audience, a task that can be time-consuming and require significant effort. It also aims to enhance collaboration among content creators by providing a centralized platform with cloud-synchronized outputs.

**Key Features & Functionalities (High-Level):**
*   **AI-Powered Content Generation:** Leverages Large Language Models (LLMs) to generate a comprehensive package from English source articles. This includes a Persian blog post (translated and SEO-optimized), title, slug, meta description, image alt text, focus keywords, and tags. It also generates social media content like Instagram posts/stories and image prompts.
*   **WordPress Integration:** Directly interacts with the WordPress REST API to automate the creation of draft posts. This includes uploading featured images and managing tags.
*   **Dual Save & Load Capabilities:**
    *   **Local Storage:** Saves all generated content as JSON files in a local `answers/` directory.
    *   **Pantry Cloud Integration:** Optionally saves and loads content to/from Pantry Cloud, enabling easy sharing and access across a team. These cloud operations are performed asynchronously.
*   **Collaboration Support:** Generated files and Pantry Cloud basket names are prefixed with the user's WordPress username (`WP_USERNAME`), making it easier to identify and manage content in a team environment.
*   **User-Friendly Web Interface:** Utilizes Streamlit to provide an interactive interface for inputting source article details, uploading images, initiating content generation, loading previous work, and publishing to WordPress.
*   **Content Processing:** Includes features like converting generated Markdown content to HTML for WordPress compatibility.

**Target User:**
The application is targeted towards content creators, bloggers, digital marketers, or editorial teams who manage a Persian-language WordPress website and wish to efficiently repurpose English content using AI. The features facilitating team collaboration (cloud storage, username prefixing) imply its suitability for small to medium-sized content teams.

---

## 📁 Project Structure

The PersiaPress AI project is organized with a clear directory structure at its root, facilitating separation of concerns between the core application logic, user-generated data, and configuration.

**Root Directory and Key Subdirectories:**

*   **Root:** The project root contains configuration files (`.gitignore`, `.python-version`, `pyproject.toml`, `uv.lock`), the main application entry point for Windows (`run.bat`), and the primary documentation (`README.md`). It also houses the main application code within the `app/` directory and related plugins in `plugins/`.
*   **`app/`:** This is the heart of the application, containing all the Python source code.
    *   `__init__.py`: Makes the `app` directory a Python package.
    *   `app.py`: The main entry point for the Streamlit web application. It likely initializes the UI and orchestrates the overall application flow.
    *   `ui.py`: Defines the user interface components using Streamlit, managing how users interact with the application (e.g., input fields, buttons, display areas).
    *   `content_generator.py`: Contains the logic for generating content using Large Language Models (LLMs). This includes crafting prompts, making calls to LLM APIs, and processing the responses to create blog posts, social media snippets, SEO metadata, etc.
    *   `llm_clients.py`: Manages the setup and initialization of LLM clients (e.g., `ChatOpenAI`), abstracting the direct interaction with LLM libraries.
    *   `wordpress_handler.py`: Handles all interactions with the WordPress REST API. This includes creating draft posts, uploading media (like featured images), and managing WordPress taxonomies (like tags and categories).
    *   `file_utils.py`: Contains utility functions for managing files and data persistence. This includes saving generated content to local JSON files (in the `answers/` directory) and interacting with Pantry Cloud for saving and loading data (using `aiohttp` for asynchronous operations).
    *   `utils.py`: Likely holds miscellaneous helper functions and utilities that are used across different parts of the application but don't fit into the more specialized modules.
*   **`answers/`:** (Typically created dynamically) This directory is designated for storing the JSON files containing the LLM-generated outputs. Files here are prefixed with the `WP_USERNAME` for better organization, especially in team environments.
*   **`images/`:** (Typically created dynamically) This directory is used to store thumbnail images uploaded by the user through the Streamlit interface before they are sent to WordPress.
*   **`plugins/`:** Contains WordPress plugins related to or required by the PersiaPress AI tool. The `ls` output shows `plugins/Rank-Math-Api-Manager/rank-math-api-manager-extended-v1.3.php`, indicating a custom plugin, likely for extending Rank Math SEO plugin functionalities via its API.

**Configuration Files:**

*   **`.env`:** (Typically gitignored) This crucial file stores environment variables and sensitive information necessary for the application to run. This includes API keys for LLMs (e.g., `GOOGLE_API_KEY`), WordPress site URL (`WP_URL`), WordPress username (`WP_USERNAME`), WordPress application password (`WP_APP_PASSWORD`), and an optional Pantry Cloud ID (`PANTRY_ID`).
*   **`pyproject.toml`:** This file is used for managing project dependencies and build system configuration, standard in modern Python projects (often used with tools like Poetry or, in this case, `uv`). It lists the libraries the project depends on.
*   **`.python-version`:** Specifies the intended Python version for the project (e.g., 3.11), ensuring a consistent development and deployment environment.
*   **`uv.lock`:** A lock file generated by the `uv` package manager, ensuring deterministic builds by pinning the exact versions of all dependencies.
*   **`.gitignore`:** Specifies intentionally untracked files and directories that Git should ignore (e.g., `.venv/`, `__pycache__/`, `.env`, `answers/`, `images/`).

---

## 🚀 Features

*   **Source Input:** Accepts English source article title, body, source name, and URL.
*   **LLM Content Package Generation:** Generates Persian Title, English Slug, Persian Content (Markdown), Meta Description, Alt Text, Focus Keywords, SEO Title, English/Persian Tags, Instagram Post/Story content, and Image Prompts.
*   **Dual Data Persistence & Loading:**
    *   Saves all generated data (including raw LLM outputs and final package) to local JSON files in `answers/`.
    *   Optionally saves the same data to Pantry Cloud if `PANTRY_ID` is configured.
    *   Filenames and Pantry basket names are prefixed with the `WP_USERNAME` for team traceability.
    *   Allows loading data from local files via `st.file_uploader`.
    *   Allows fetching a list of baskets from Pantry Cloud and loading selected data.
*   **Asynchronous Pantry Operations:** All interactions with Pantry Cloud (saving, listing baskets, getting basket content) are performed asynchronously using `aiohttp`.
*   **WordPress Post Creation Workflow:** (As previously described, including Markdown to HTML, tag handling, image upload, Rank Math attempt).
*   **Local Image Handling:** (As previously described).

---

## 🔄 Application Workflow

The PersiaPress AI application follows a user-driven workflow, orchestrated by the Streamlit interface defined in `app/ui.py`.

**1. Initialization and LLM Client Setup:**
*   When the user launches the application (`streamlit run app/app.py`), the `main()` function in `app/ui.py` is executed.
*   It first checks for the `GOOGLE_API_KEY` environment variable. If not found, it displays an error and stops.
*   It then calls `initialize_llm_clients()` from `app/llm_clients.py` to set up the necessary Large Language Model clients. If this fails, an error is displayed.

**2. User Input for New Content Generation:**
*   The UI presents input fields for the English source title, body, source name, and URL.
*   Checkboxes allow the user to select optional content like Instagram texts, story teasers, and an Iranian Farsi video prompt.

**3. (Optional) Loading Previous Work:**
   Users can load previously generated content:
*   **Local File Upload:** Via `st.file_uploader` for JSON files from the `answers/` folder.
*   **Pantry Cloud Loading:** If `PANTRY_ID` is configured, users can fetch and select baskets from Pantry Cloud.

**4. Content Generation Process:**
*   Clicking "✨ Generate Persian Blog Post Package" triggers `generate_persian_blog_package()` from `app/content_generator.py`.
*   This function uses the initialized LLM clients and source details to produce the Persian blog package, SEO metadata, image prompts, etc.
*   **Data Saving (Automatic):** The generated output is saved locally (to `answers/`) and to Pantry Cloud (if configured) by functions in `app/file_utils.py`.

**5. Displaying Generated/Loaded Content:**
*   The UI presents the generated or loaded data in expandable sections (Metadata, Blog Content, Image Prompts, Instagram Content, etc.).

**6. Thumbnail Image Upload (Blog):**
*   Users can upload a thumbnail image, which is saved locally to the `images/` directory in WEBP format.

**7. Publishing to WordPress:**
*   Clicking "Create Draft Post in WordPress" calls `create_draft_post()` from `app/wordpress_handler.py`.
*   This function sends the title, content, slug, tags, SEO metadata, and the locally saved image (if found) to the WordPress REST API to create a draft post.

---

## 📋 Requirements

1.  **Software:**
    *   Python 3.11
    *   `uv` package manager (recommended)
    *   WordPress site with REST API & Application Password.
    *   OpenAI-compatible API access.
    *   (Optional) Custom Rank Math API plugin.
2.  **Dependencies:** (Managed via `pyproject.toml` and `uv.lock`)
    *   `dotenv>=0.9.9`
    *   `langchain-core>=0.3.58`
    *   `langchain-openai>=0.3.16`
    *   `markdown>=3.8`
    *   `streamlit>=1.45.0`
    *   `aiohttp>=3.8.0` (for asynchronous Pantry operations)
    *   `requests` (for WordPress synchronous operations, often a sub-dependency)
    *   `Pillow`
3.  **Environment Setup:**
    *   Create a `.env` file in the project root.
    *   Populate it with:

    ```env
    # LLM Configuration
    GOOGLE_API_KEY=your_google_api_key_for_avalai 

    # WordPress Configuration
    WP_URL=https://your-wordpress-site.com 
    WP_USERNAME=your_wordpress_username_for_author_and_filename_prefix
    WP_APP_PASSWORD=your_wordpress_application_password

    # Pantry Cloud (Optional)
    # PANTRY_ID=your_pantry_cloud_id 
    ```
    _Ensure `WP_USERNAME` is set for file/basket naming. If `PANTRY_ID` is provided, cloud features are enabled._

---

## 💻 Installation & Launch Instructions

1.  **Clone Repository**
2.  **Install Dependencies** (Using `uv sync`)
    ```bash
    uv sync
    ```
3.  **Configure Environment** (Create and populate `.env` as described above).
4.  **Launch Application**
    ```bash
    streamlit run app/app.py
    ```
    (Or use `run.bat` on Windows).

---

## 📝 Usage Guide

1.  Launch and access the Streamlit app.
2.  **Input Source:** Fill in English article details.
3.  **Generate Content:** Click "✨ Generate Persian Blog Post Package".
    *   Optionally select/deselect checkboxes for Instagram post/story generation.
4.  **Review Output:** Examine generated content. Outputs are automatically saved locally and to Pantry if configured.
5.  **Upload Thumbnail:** Use the image uploader.
6.  **(Optional) Load Existing Output:**
    *   **Local:** Use the "Upload a previously generated .json file".
    *   **Pantry Cloud:** If configured, use the "Load from Pantry Cloud" section.
7.  **Create WordPress Draft:** Click "🚀 Create Draft Post in WordPress".
8.  **Verify:** Check WordPress admin.

---

## ⚙️ Technical Implementation Details

### LLM Usage
*   Uses `langchain-openai`'s `ChatOpenAI` client via `app.llm_clients`.
*   Content generation is orchestrated in `app.content_generator` with detailed prompts.

### WordPress Interaction (`requests`)
*   Managed by `app.wordpress_handler`.
*   Uses `requests` for synchronous communication with WordPress REST API.

### Data Persistence & Cloud Sync (`app.file_utils`, `aiohttp`)
*   `app.file_utils` contains logic for data handling.
*   Local saves: JSON files to `answers/`, prefixed with sanitized `WP_USERNAME`.
*   Pantry Cloud: If `PANTRY_ID` is set, saves to Pantry using `aiohttp` for asynchronous `POST` requests. Basket names are also prefixed with username.
*   Pantry Loading: Lists baskets and fetches content asynchronously using `aiohttp`.

### UI (`streamlit`)
*   Managed by `app.ui` and `app.app`.
*   Uses `asyncio.run` to integrate asynchronous Pantry loading functions into Streamlit's synchronous flow.

### File Handling & Logging
*   Standard Python libraries (`os`, `dotenv`, `logging`, `markdown`, `Pillow`, `mimetypes`).

---

## 🛠️ Key Technologies Used

The PersiaPress AI project leverages a combination of modern Python libraries and technologies:

*   **Core Python Version:** Python 3.11
*   **Web Framework:** Streamlit (`streamlit>=1.45.0`)
*   **LLM Interaction Libraries:** Langchain (`langchain-core>=0.3.58`, `langchain-openai>=0.3.16`)
*   **WordPress Interaction:** WordPress REST API (using `requests` library for HTTP communication)
*   **Data Handling and Cloud Storage:**
    *   JSON (Python standard library) for local data.
    *   Pantry Cloud with `aiohttp>=3.8.0` for asynchronous cloud operations.
    *   Pillow for image processing.
    *   Markdown (`markdown>=3.8`) for content conversion.
*   **Dependency Management & Configuration:**
    *   `uv` package manager with `pyproject.toml` and `uv.lock`.
    *   `python-dotenv` (`dotenv>=0.9.9`) for environment variable management.

---

## 📈 Current Status & Future Plans

### Current Status
*   Core workflow functional: LLM generation, local/Pantry saving (with username prefix), loading from local/Pantry, WordPress draft creation.
*   Pantry operations are asynchronous.
*   Rank Math API integration remains potentially unreliable.
*   Non-ASCII tag creation via API is disabled.

### Future Enhancements
*   Resolving network/SSL errors for WordPress.
*   Improving Rank Math integration.
*   Solution for non-ASCII tags.
*   More robust error handling.
*   Internal linking.
*   Testing.

---

## 🙌 Acknowledgments

*   No explicit acknowledgments or credits to third-party libraries (beyond dependencies) or individuals were identified within the source code comments or docstrings.

---

## 📜 License

*   No `LICENSE` file was found in the project root.
*   The `pyproject.toml` file does not specify a license.
*   The license for this project is therefore unclear or missing.

---
