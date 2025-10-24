import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file and configure Gemini API
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_keywords(content):
    """Extracts the 5 most important, high-value SEO keywords from content using Gemini API.
    
    Args:
        content: The text content to extract keywords from
        
    Returns:
        List of 13 most relevant keywords
    """
    prompt = f"""
You are an expert SEO auditor and content strategist working to meet company standards for digital marketing and SEO audits.
Your task is to extract the most important, high-value, and SEO-relevant keywords from the provided company content for an SEO audit report.

Guidelines:
- Extract exactly 5 most important keywords or key phrases that best represent the main topic.
- Focus on the most specific and high-impact terms only.
- Avoid generic, filler, or overly broad terms (e.g., 'data', 'business', 'company').
- Ensure keywords are highly targeted and SEO-optimized.
-- Output only 13 keywords, separated by commas, with no extra text.

Few-shot examples:
Input: Content: Tata Consultancy Services (TCS) is an Indian multinational information technology (IT) services and consulting company headquartered in Mumbai, India.
Output: Tata Consultancy Services, IT services, digital transformation, enterprise technology, global consulting

Input: Content: This page is about enterprise SEO audits and digital marketing analytics for large companies.
Output: enterprise SEO audit, digital marketing analytics, SEO strategy, performance optimization, data-driven marketing

Input: Content: The company specializes in cloud computing, artificial intelligence, and cybersecurity solutions for enterprise clients.
Output: cloud computing, artificial intelligence, cybersecurity solutions, enterprise technology, digital transformation

Input: Content: Infosys provides digital transformation and IT services to global enterprises.
Output: digital transformation, IT services, enterprise solutions, global technology, business innovation

Input: Content: This report covers the implementation of robotic process automation (RPA) in banking.
Output: robotic process automation, RPA implementation, banking automation, process optimization, financial technology

Input: Content:
{content}
Output:
"""
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, generation_config={"temperature": 0})
        keywords = [kw.strip() for kw in response.text.split(",") if kw.strip()]
        return keywords[:5]
    except Exception as e:
        print(f"Gemini keyword extraction error: {e}")
        return []
