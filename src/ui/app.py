import streamlit as st
from src.database.manager import DatabaseManager
from src.config.settings import settings
from src.ui.papers_view import display_papers

def main():
    st.set_page_config(
        page_title="Paper Search",
        page_icon="📚",
        layout="wide"
    )
    
    # Initialize database connection
    db_manager = DatabaseManager(settings.DATABASE_URL)
    
    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Papers", "Statistics", "Settings"]
    )
    
    if page == "Papers":
        display_papers(db_manager)
    elif page == "Statistics":
        st.title("Statistics")
        st.write("Coming soon...")
    else:
        st.title("Settings")
        st.write("Coming soon...")

if __name__ == "__main__":
    main()
