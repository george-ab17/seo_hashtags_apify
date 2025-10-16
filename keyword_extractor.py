import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file and configure Gemini API
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_keywords(content):
    """
    Extracts the most important, high-value SEO keywords from content using Gemini API.
    """
    prompt = f"""
You are an expert SEO auditor and content strategist working to meet company standards for digital marketing and SEO audits.
Your task is to extract the most important, high-value, and SEO-relevant keywords from the provided company content for an SEO audit report.

Guidelines:
- Only extract keywords and key phrases that are highly relevant to the main topic and business context.
- Avoid generic, filler, or overly broad terms (e.g., 'data', 'business', 'company').
- Include both single-word and multi-word phrases that are suitable for hashtags, search optimization, and professional reporting.
- Rank keywords by importance and specificity to the content.
- Output a comma-separated list of 15-20 keywords or key phrases, with no extra text.

Few-shot examples:
Input: Content: Tata Consultancy Services (TCS) is an Indian multinational information technology (IT) services and consulting company headquartered in Mumbai, India. TCS is a part of the Tata Group and operates in 46 countries.
Output: Tata Consultancy Services, TCS, IT services, consulting, Tata Group, multinational IT, digital transformation, technology consulting, Mumbai, global IT solutions, business process outsourcing, enterprise technology, software services, IT consulting, Indian IT company

Input: Content: This page is about enterprise SEO audits and digital marketing analytics for large companies.
Output: enterprise SEO audit, digital marketing analytics, SEO audit, large companies, SEO compliance, marketing analytics, SEO reporting, enterprise marketing, SEO strategy, audit report, digital analytics, SEO optimization, business SEO, corporate SEO, SEO insights

Input: Content: Infosys Limited is a global leader in next-generation digital services and consulting. The company enables clients in 50 countries to navigate their digital transformation.
Output: Infosys Limited, digital services, consulting, global IT, digital transformation, next-generation IT, business consulting, technology solutions, IT outsourcing, global clients, enterprise IT, digital innovation, IT strategy, technology consulting, multinational IT company

Input: Content: The company specializes in cloud computing, artificial intelligence, and cybersecurity solutions for enterprise clients.
Output: cloud computing, artificial intelligence, cybersecurity, enterprise clients, cloud solutions, AI solutions, cybersecurity services, IT security, enterprise technology, digital security, cloud infrastructure, AI for business, enterprise cybersecurity, technology consulting, secure cloud

Input: Content: This report covers the implementation of robotic process automation (RPA) and workflow optimization in financial services.
Output: robotic process automation, RPA, workflow optimization, financial services, process automation, automation implementation, finance automation, workflow management, RPA solutions, business process automation, automation strategy, financial technology, workflow improvement, RPA deployment, finance workflow

Input: Content:
{content}
Output:
"""
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, generation_config={"temperature": 0})
        keywords = [kw.strip() for kw in response.text.split(",") if kw.strip()]
        return keywords
    except Exception as e:
        print(f"Gemini keyword extraction error: {e}")
        return []
