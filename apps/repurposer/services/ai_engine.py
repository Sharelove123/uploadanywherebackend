
import os
import logging
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class AIEngine:
    """Service to interact with Google Gemini API."""

    def __init__(self):
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_post(self, content: str, platform: str, brand_voice=None) -> dict:
        """
        Generates a structured social media post for a specific platform.
        Returns a dictionary with keys: content, hook, hashtags, thread_posts (optional).
        """
        try:
            prompt = self._build_prompt(content, platform, brand_voice)
            
            # Use JSON mode for structured output if supported, or prompt engineering
            # For Gemini 1.5 Flash, we can request JSON response
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                response_mime_type="application/json"
            )
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            import json
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                # Fallback if model returns raw text despite instructions
                return {
                    "content": response.text,
                    "hook": response.text[:50] + "...",
                    "hashtags": []
                }
                
        except Exception as e:
            logger.error(f"Error generating content for {platform}: {str(e)}")
            return {
                "content": f"Error: {str(e)}",
                "hook": "Error",
                "hashtags": []
            }

    def _build_prompt(self, content: str, platform: str, brand_voice=None) -> str:
        """Constructs a specific prompt for the target platform requesting JSON."""
        
        voice_instruction = ""
        if brand_voice:
            voice_instruction = f"Use the following brand voice/style: {brand_voice.name}. {brand_voice.description}"

        base_prompt = f"""
        You are an expert social media manager. I will provide you with content.
        Your task is to repurpose this into a high-quality post for {platform}.
        {voice_instruction}
        
        Return the result strictly as a valid JSON object with the following schema:
        {{
            "hook": "Attention grabbing opening line",
            "content": "The main body of the post",
            "hashtags": ["tag1", "tag2"],
            "thread_posts": ["tweet 1", "tweet 2"] (ONLY if platform is twitter, else null)
        }}

        Here is the content:
        "{content[:25000]}..." (truncated)
        """
        
        return base_prompt
