import sys
import os

# Explicitly add the project root directory (one level up from 'app') to sys.path
# This is needed so streamlit run app/app.py can find the 'app' package for the next import
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now, the absolute import should find the 'app' package in the modified sys.path
# We import 'main' from app.ui, which itself uses relative imports internally
from app.ui import main

if __name__ == "__main__":
    # Run the main UI function from ui.py
    main() 