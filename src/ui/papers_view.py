import streamlit as st
import pandas as pd
from typing import List, Dict
import json
from database.manager import DatabaseManager
from config.settings import settings

def format_authors(authors_json: str) -> str:
    """Format authors JSON string into readable text"""
    try:
        authors = json.loads(authors_json)
        return ", ".join(author['name'] for author in authors)
    except:
        return authors_json

def display_papers(db_manager: DatabaseManager):
    """Display papers in an interactive table"""
    st.title("Research Papers")
    
    # Get all papers from database
    papers = db_manager.get_processed_papers()
    
    # Debug information
    st.write(f"Total papers retrieved from database: {len(papers)}")
    
    # Convert to DataFrame with error handling
    papers_data = []
    for paper in papers:
        try:
            paper_dict = {
                'Title': paper.title or "No Title",
                'Authors': format_authors(paper.authors) if paper.authors else "No Authors",
                'Year': paper.year or 0,
                'Venue': paper.venue or "N/A",
                'Journal': paper.journal or "N/A",
                'Citations': paper.citation_count or 0,
                'References': paper.reference_count or 0,
                'Relevance': float(getattr(paper, 'relevance_score', 0) or 0),
                'Open Access': "Yes" if paper.is_open_access else "No",
                'Links': f"[Paper]({paper.url})" if paper.url else "N/A",
                'PDF': f"[PDF]({paper.pdf_url})" if paper.pdf_url else "N/A",
                'ID': paper.paper_id
            }
            papers_data.append(paper_dict)
        except Exception as e:
            st.error(f"Error processing paper {paper.paper_id}: {str(e)}")
            continue
    
    if not papers_data:
        st.warning("No papers found in the database.")
        return
        
    df = pd.DataFrame(papers_data)
    
    # Debug information
    st.write(f"Papers loaded into DataFrame: {len(df)}")
    if len(df) > 0:
        st.write("Sample of data:", df.head())
    
    # Add filters
    col1, col2 = st.columns(2)
    with col1:
        min_year = st.number_input('Minimum Year', 
                                 min_value=int(df['Year'].min()) if len(df) > 0 else 1900,
                                 max_value=int(df['Year'].max()) if len(df) > 0 else 2024,
                                 value=int(df['Year'].min()) if len(df) > 0 else 2000)
    with col2:
        min_relevance = st.slider('Minimum Relevance Score', 0.0, 10.0, 0.0)
    
    # Filter DataFrame with error handling
    try:
        filtered_df = df[
            (df['Year'].fillna(0).astype(int) >= min_year) &
            (df['Relevance'].fillna(0).astype(float) >= min_relevance)
        ]
    except Exception as e:
        st.error(f"Error filtering data: {str(e)}")
        filtered_df = df
    
    # Display table with sorting and updated columns
    st.dataframe(
        filtered_df,
        column_config={
            'Title': st.column_config.TextColumn('Title', width='large'),
            'Authors': st.column_config.TextColumn('Authors', width='medium'),
            'Year': st.column_config.NumberColumn('Year'),
            'Venue': st.column_config.TextColumn('Venue', width='medium'),
            'Journal': st.column_config.TextColumn('Journal', width='medium'),
            'Citations': st.column_config.NumberColumn('Citations'),
            'References': st.column_config.NumberColumn('References'),
            'Relevance': st.column_config.NumberColumn('Relevance Score', format="%.1f"),
            'Open Access': st.column_config.TextColumn('Open Access', width='small'),
            'Links': st.column_config.LinkColumn('Paper Link'),
            'PDF': st.column_config.LinkColumn('PDF Link'),
            'ID': st.column_config.TextColumn('Paper ID', width='small')
        },
        hide_index=True,
        use_container_width=True
    )

    # Display stats
    if len(filtered_df) > 0:
        st.sidebar.markdown("## Statistics")
        st.sidebar.markdown(f"Total Papers: {len(df)}")
        st.sidebar.markdown(f"Filtered Papers: {len(filtered_df)}")
        st.sidebar.markdown(f"Average Relevance: {filtered_df['Relevance'].mean():.2f}")
