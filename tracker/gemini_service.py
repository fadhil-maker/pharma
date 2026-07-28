import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure Gemini API
# Try to load .env file from the root
env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set in environment or .env file! Lazy Loading will fail.")

def check_drug_interaction(drug_a, drug_b):
    """
    Queries Gemini for an interaction between drug_a and drug_b.
    Expects a strict JSON response.
    Returns a dictionary or None if no interaction (Severity 0).
    """
    if not GEMINI_API_KEY:
        return None

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a clinical pharmacologist. I need to know if there is a medically significant interaction between "{drug_a}" and "{drug_b}".
    
    If there is absolutely NO significant systemic interaction, or if they are perfectly safe to take together with no dosage adjustments needed, you MUST return Severity 0.
    
    Respond ONLY with a valid JSON object matching this exact structure:
    {{
        "severity": <integer from 0 to 10>,
        "cause": "<string explaining the pharmacological or pharmacokinetic cause, max 400 chars. Leave empty if severity is 0>",
        "remedy": "<string explaining clinical management or dosage adjustment. Leave empty if severity is 0>"
    }}
    
    Ensure your response contains ONLY the JSON, with no markdown formatting or extra text.
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"temperature": 0.1})
        text = response.text.strip()
        
        # Remove markdown code blocks if the model wrapped it
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        data = json.loads(text.strip())
        
        # If Gemini determined it is safe or has no interaction, return None so it is discarded!
        if data.get('severity', 0) == 0:
            return None
            
        return {
            'severity': data.get('severity', 1),
            'cause': data.get('cause', 'Unknown clinical synergy.'),
            'remedy': data.get('remedy', 'Monitor patient closely.')
        }
        
    except Exception as e:
        logger.error(f"Gemini AI error for {drug_a} + {drug_b}: {str(e)}")
        return None
