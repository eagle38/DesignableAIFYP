# gemini_client.py
from google import genai

# 1. INITIALIZE THE NEW CLIENT
# Replace with your validated API Key
API_KEY = "AQ.Ab8RN6JN1lBDV_NyRQSs8QkTTCIC_W_ZNi9enFeS0j3resWOAQ" 
client = genai.Client(api_key=API_KEY)

# This dictionary stores the history of the conversation
# Note: The new SDK handles history slightly differently, 
# but we will keep this simple for your current frontend.
sessions = {}

def call_designable_ai(session_id, prompt_payload):
    """
    Calls the modern Gemini API using the google-genai library.
    """
    # Use the model that worked in your test (e.g., gemini-2.0-flash or gemini-3-flash-preview)
    model_id = "gemini-3-flash-preview" 
    
    try:
        # 2. GENERATE CONTENT WITH SYSTEM INSTRUCTIONS
        response = client.models.generate_content(
            model=model_id,
            config={
                "system_instruction": prompt_payload["system_prompt"],
                "temperature": 0.7, # Adds a touch of creative 'Architect' flair
            },
            contents=prompt_payload["prompt"]
        )
        
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg:
            return "Architectural Error: Google's design servers are temporarily overloaded. Please retry in 30 seconds."
        if "429" in error_msg:
            return "Architectural Error: Quota reached. Please wait a moment for the 'Architect' to finish the current review."
        
        return f"Architectural Error: {error_msg}"