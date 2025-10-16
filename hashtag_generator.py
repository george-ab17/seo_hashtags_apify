import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file and configure Gemini API
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_hashtags(keywords):
    """
    Generate 20 professional, SEO-friendly hashtags using Gemini API, using both keywords and cleaned HTML content.
    """
    # Accept both keywords and content
    if isinstance(keywords, tuple) and len(keywords) == 2:
        keywords, content = keywords
    else:
        content = ""
    prompt = f"""
You are an expert SEO auditor and social media strategist working to meet company standards for digital marketing.
Your task is to generate 20 unique, professional, SEO-friendly, and currently trending hashtags for a company SEO audit report.

Guidelines:
- Focus on hashtags that are highly relevant to the provided keywords and page content.
- All hashtags must be suitable for a company or enterprise context (no slang, no generic terms like #business or #data).
- Prefer hashtags that are currently trending in the SEO, analytics, automation, and digital transformation domains.
- Avoid generic, unrelated, or overused hashtags.
- Each hashtag should be concise, easy to read, and follow company branding standards.
- Output exactly 20 hashtags, separated by commas, with no extra text.

Few-shot examples:
Input: Keywords: SEO Audit, Digital Marketing, Analytics
Page Content: This page is about enterprise SEO audits and digital marketing analytics for large companies.
Output: #SEOAudit, #DigitalMarketing, #EnterpriseSEO, #MarketingAnalytics, #CompanySEO, #SEOStandards, #AuditReport, #DigitalStrategy, #AnalyticsForBusiness, #CorporateSEO, #SEOCompliance, #SEOInsights, #SEOConsulting, #SEOOptimization, #SEOReview, #SEOExperts, #SEOEnterprise, #SEOAnalysis, #SEOReporting, #SEOTrends

Input: Keywords: Process Automation, Workflow Optimization
Page Content: This page covers process automation and workflow optimization for business efficiency.
Output: #ProcessAutomation, #WorkflowOptimization, #BusinessEfficiency, #AutomationStrategy, #WorkflowAutomation, #ProcessImprovement, #BusinessAutomation, #OperationalExcellence, #AutomationSolutions, #WorkflowManagement, #ProcessOptimization, #DigitalAutomation, #AutomationTrends, #BusinessProcess, #EfficiencyExperts, #ProcessInnovation, #AutomationConsulting, #WorkflowExperts, #ProcessExcellence, #AutomationForBusiness

Input: Keywords: Infosys, Digital Services, Consulting
Page Content: Infosys Limited is a global leader in next-generation digital services and consulting. The company enables clients in 50 countries to navigate their digital transformation.
Output: #Infosys, #DigitalServices, #ITConsulting, #GlobalIT, #DigitalTransformation, #NextGenIT, #BusinessConsulting, #TechSolutions, #ITOutsourcing, #EnterpriseIT, #DigitalInnovation, #ITStrategy, #ConsultingExperts, #ITGlobal, #DigitalConsulting, #ITLeaders, #TechConsulting, #ITForBusiness, #InnovationLeaders, #ITClients

Input: Keywords: Cloud Computing, Artificial Intelligence, Cybersecurity
Page Content: The company specializes in cloud computing, artificial intelligence, and cybersecurity solutions for enterprise clients.
Output: #CloudComputing, #ArtificialIntelligence, #Cybersecurity, #EnterpriseTech, #CloudSolutions, #AISolutions, #CybersecurityServices, #ITSecurity, #DigitalSecurity, #CloudInfrastructure, #AIForBusiness, #EnterpriseCybersecurity, #TechConsulting, #SecureCloud, #CloudExperts, #AIEdge, #CloudSecurity, #AIDriven, #EnterpriseSolutions, #TechInnovation

Input: Keywords: Robotic Process Automation, Financial Services
Page Content: This report covers the implementation of robotic process automation (RPA) and workflow optimization in financial services.
Output: #RoboticProcessAutomation, #RPA, #WorkflowOptimization, #FinancialServices, #ProcessAutomation, #AutomationImplementation, #FinanceAutomation, #WorkflowManagement, #RPASolutions, #BusinessProcessAutomation, #AutomationStrategy, #Fintech, #WorkflowImprovement, #RPADriven, #FinanceWorkflow, #AutomationForFinance, #ProcessInnovation, #FinanceTech, #RPAExperts, #AutomationConsulting

Input:
Keywords:
{', '.join(keywords)}
Page Content:
{content}
Output:
"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, generation_config={"temperature": 0})
        hashtags = [tag.strip().replace(' ', '') if tag.strip().startswith('#') else '#' + tag.strip().replace(' ', '') for tag in response.text.split(",") if tag.strip()]
        return hashtags[:20]
    except Exception as e:
        print(f"Gemini hashtag generation error: {e}")
        return []
    for tag in response.text.split(","):
        clean_tag = tag.strip().replace(' ', '')
        # Ensure single leading '#'
        if not clean_tag.startswith('#'):
            clean_tag = '#' + clean_tag
        else:
            clean_tag = '#' + clean_tag.lstrip('#')
        hashtags.append(clean_tag)
    hashtags = hashtags[:20]
    return hashtags
