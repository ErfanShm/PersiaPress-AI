# 📄 PersiaPress AI

Automate your WordPress workflow: Generate Persian blog posts from English sources using AI and publish drafts instantly.

Welcome to the **PersiaPress AI** repository! This project implements a Streamlit-based web application designed to streamline the process of creating Persian blog content for a WordPress website (`hooshews.com`) from English source material, leveraging Large Language Models (LLMs). It supports saving generated content both locally and to Pantry Cloud, and allows loading previous work from both sources.

The application consists of the following core components:
- **Streamlit UI (`app/ui.py`, `app/app.py`):** Provides the web interface for user input (source article details, image upload), loading previous work, and output display.
- **Content Generation Logic (`app/content_generator.py`):** Handles the core logic of orchestrating LLM calls to generate various content pieces (blog posts, Instagram texts, story teasers, image prompts).
- **LLM Client Management (`app/llm_clients.py`):** Manages the initialization of LLM clients (e.g., `ChatOpenAI`).
- **WordPress Interaction (`app/wordpress_handler.py`):** Contains functions for interacting with the WordPress REST API (creating posts, uploading media, managing tags, etc.).
- **File & Pantry Utilities (`app/file_utils.py`):** Manages saving output locally and to Pantry Cloud (using `aiohttp` for async operations), loading from Pantry, and other file-related utilities.
- **General Utilities (`app/utils.py`):** May contain other miscellaneous helper functions.
- **Configuration (`dotenv`):** Manages sensitive information like API keys, WordPress credentials, and Pantry ID.

This tool aims to automate the translation, SEO optimization, and initial drafting process for blog posts, enhancing collaboration through cloud-synced outputs identified by username.

---

## ✨ Overview

This project provides a web interface built with Streamlit that takes details of an English source article. It then uses configured LLM clients to generate a comprehensive Persian blog post package. This package includes translated and SEO-optimized content, metadata (title, slug, meta description, image alt text, tags, focus keywords), and social media content (Instagram posts & stories, image prompts). The application can save these outputs locally and to Pantry Cloud, with filenames/basket names prefixed by username for team collaboration. Users can also load previously generated work from either local storage or Pantry Cloud. Finally, it interacts with a WordPress site's REST API to automatically create draft posts.

Key features include:

*   **LLM-Powered Content Generation:** Utilizes LLMs for a full Persian blog package and social media content from English input.
*   **WordPress Draft Creation:** Automates draft post creation via the WordPress REST API.
*   **Dual Save & Load:**
    *   Saves generated outputs locally (in `answers/`) and to Pantry Cloud.
    *   Allows loading previous work from local JSON files or Pantry Cloud baskets.
*   **Username Prefixing:** Prepends `WP_USERNAME` (from `.env`) to saved filenames and Pantry basket names for easy identification in team environments.
*   **Asynchronous Cloud Operations:** Uses `aiohttp` for non-blocking communication with Pantry Cloud.
*   **Markdown to HTML Conversion & Tag Management.**
*   **Featured Image Upload & Handling.**
*   **Streamlit Web Interface.**
*   **(Attempted) Rank Math Integration.**

---

## 🗂️ File Structure

```
.
├── .git/                     # Git version control files
├── .venv/                    # Python virtual environment (ignored by Git)
├── app/                      # Core application source code
│   ├── __init__.py           # Makes 'app' a Python package
│   ├── app.py                # Main Streamlit application entry point
│   ├── ui.py                 # Defines the Streamlit user interface components
│   ├── content_generator.py  # Handles LLM orchestration for content
│   ├── llm_clients.py        # Manages LLM client initialization
│   ├── wordpress_handler.py  # WordPress API interaction logic
│   ├── file_utils.py         # Local file and Pantry Cloud utilities
│   └── utils.py              # Miscellaneous utility functions
├── answers/                  # Directory for storing LLM output JSON files (prefixed by username)
├── images/                   # Directory for storing uploaded thumbnail images
├── plugins/                  # Contains related plugins (e.g., for WordPress)
│   └── rank-math-api-manager-extended-v1.3.zip # Custom Rank Math API plugin
├── .gitignore                # Specifies intentionally untracked files for Git
├── .python-version           # Specifies the intended Python version (3.11)
├── pyproject.toml            # Project metadata and dependencies
├── README.md                 # This file
└── uv.lock                   # Lock file for dependencies managed by UV
```

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
    *   `requests` (for WordPress synchronous operations)
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
    (This will install `aiohttp` and other dependencies from `uv.lock`).
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
4.  **Review Output:** Examine generated content. Outputs are automatically saved locally (e.g., `answers/your_username_0001_slug_timestamp.json`) and to Pantry if configured.
5.  **Upload Thumbnail:** Use the image uploader.
6.  **(Optional) Load Existing Output:**
    *   **Local:** Use the "Upload a previously generated .json file" to load a file from your computer.
    *   **Pantry Cloud:** If `PANTRY_ID` is set, use the "Load from Pantry Cloud" section. Click "Fetch Baskets from Pantry", select a basket (e.g., `your_username_0001_slug_timestamp`), and click "Load Selected Pantry Basket".
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

## 📈 Current Status & Future Plans

### Current Status
*   Core workflow functional: LLM generation, local/Pantry saving (with username prefix), loading from local/Pantry, WordPress draft creation.
*   Pantry operations are asynchronous.
*   Rank Math API integration remains potentially unreliable.
*   Non-ASCII tag creation via API is disabled.

### Future Enhancements
*   (No change from previous, potential improvements still valid)
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
