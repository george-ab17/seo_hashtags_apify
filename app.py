import streamlit as st
import os
from main import main
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="SEO Hashtag Generator",
    page_icon="🔍",
    layout="wide"
)

# Title and description
st.title("🔍 SEO Hashtag Generator")
st.markdown("""
This tool helps you generate relevant and trending hashtags for your content by:
1. Analyzing your webpage content
2. Extracting relevant keywords
3. Generating hashtags using AI
4. Finding trending hashtags related to your content
""")

# Create two columns for input
col1, col2 = st.columns([2, 1])

with col1:
    # URL input
    url = st.text_input("Enter URL to analyze:", placeholder="https://example.com")

with col2:
    # Keywords input (optional)
    keywords = st.text_input(
        "Enter optional keywords (comma-separated):",
        placeholder="keyword1, keyword2, keyword3"
    )

# Process button
if st.button("Generate Hashtags", type="primary"):
    if not url:
        st.error("Please enter a URL to analyze")
    else:
        try:
            with st.spinner("Analyzing content and generating hashtags..."):
                # Process keywords if provided
                user_keywords = [k.strip() for k in keywords.split(",")] if keywords else None
                
                # Create tabs for displaying results
                result_tab, debug_tab = st.tabs(["Results 📊", "Debug Info 🔧"])
                
                # Capture stdout to display debug info
                import io
                import sys
                old_stdout = sys.stdout
                sys.stdout = mystdout = io.StringIO()
                
                # Run the main process
                result = main(url, user_keywords)
                
                # Get debug output
                debug_output = mystdout.getvalue()
                sys.stdout = old_stdout
                
                # Display results in the Results tab
                with result_tab:
                    if result and 'apify_trending_hashtags' in result:
                        # Display trending hashtags
                        st.subheader("📈 Top Trending Hashtags")
                        hashtag_cols = st.columns(4)
                        for i, hashtag in enumerate(result['apify_trending_hashtags']):
                            hashtag_cols[i % 4].markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>{hashtag}</div>", unsafe_allow_html=True)
                        
                        # Display keywords used
                        st.subheader("🎯 Keywords Used")
                        st.write(", ".join(result['used_keywords']))
                        
                        # Add copy buttons
                        st.subheader("📋 Copy Options")
                        col1, col2 = st.columns(2)
                        with col1:
                            hashtags_text = " ".join(result['apify_trending_hashtags'])
                            st.text_area("Copy hashtags (space-separated)", hashtags_text, height=100)
                        with col2:
                            hashtags_text_newline = "\n".join(result['apify_trending_hashtags'])
                            st.text_area("Copy hashtags (one per line)", hashtags_text_newline, height=100)
                    else:
                        st.error("No results generated. Please check the debug tab for more information.")
                
                # Display debug info in the Debug tab
                with debug_tab:
                    st.code(debug_output)
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Add footer with environment status
st.markdown("---")
status_col1, status_col2 = st.columns(2)
with status_col1:
    if os.getenv("APIFY_API_TOKEN"):
        st.success("✅ Apify API Token configured")
    else:
        st.warning("⚠️ Apify API Token not found")

with status_col2:
    if os.getenv("GEMINI_API_KEY"):
        st.success("✅ Gemini API Key configured")
    else:
        st.warning("⚠️ Gemini API Key not found")

# Add instructions for setting up API keys
with st.expander("ℹ️ Setup Instructions"):
    st.markdown("""
    To use this tool, you need to set up your API keys in a `.env` file:
    1. Create a file named `.env` in the project directory
    2. Add your API keys:
        ```
        APIFY_API_TOKEN=your_apify_token_here
        GEMINI_API_KEY=your_gemini_api_key_here
        ```
    3. Restart the application
    """)