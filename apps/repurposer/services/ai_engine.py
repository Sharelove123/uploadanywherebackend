
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
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def generate_post(self, content: str, platform: str, brand_voice=None, source_url=None, user_prompt=None) -> dict:
        """
        Generates a structured social media post for a specific platform.
        Returns a dictionary with keys: content, hook, hashtags, thread_posts (optional).
        """
        try:
            prompt = self._build_prompt(content, platform, brand_voice, user_prompt)
            
            # Use JSON mode for structured output if supported, or prompt engineering
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                response_mime_type="application/json"
            )
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            import json
            try:
                result = json.loads(response.text)
                
                # Post-processing: Append URL if needed
                if source_url:
                    if platform == 'linkedin':
                        if 'content' in result:
                            result['content'] += f"\n\n🔗 Source: {source_url}"
                    elif platform == 'twitter':
                        # For threads, add link to last post or first post
                        if 'thread_posts' in result and result['thread_posts']:
                            result['thread_posts'][-1] += f" {source_url}"
                        elif 'content' in result:
                            result['content'] += f" {source_url}"
                    elif platform in ['youtube', 'instagram']:
                        if 'content' in result:
                            result['content'] += f"\n\n🔗 Original: {source_url}"
                            
                return result
            except json.JSONDecodeError:
                text = response.text
                if source_url:
                    text += f"\n\n{source_url}"
                return {
                    "content": text,
                    "hook": text[:50] + "...",
                    "hashtags": []
                }
                
        except Exception as e:
            logger.error(f"Error generating content for {platform}: {str(e)}")
            return {
                "content": f"Error: {str(e)}",
                "hook": "Error",
                "hashtags": []
            }

    def _build_prompt(self, content: str, platform: str, brand_voice=None, user_prompt=None) -> str:
        """Constructs a specific prompt for the target platform requesting JSON."""
        
        voice_instruction = ""
        if brand_voice:
            voice_instruction = f"Use the following brand voice/style: {brand_voice.name}. {brand_voice.description}"
        else:
            voice_instruction = "Write in a professional yet engaging, human-like tone. Avoid buzzwords. Be punchy."

        custom_instruction = ""
        if user_prompt:
            custom_instruction = f"IMPORTANT - User's Custom Instruction: {user_prompt}"

        platform_instruction = ""
        if platform == 'twitter':
            platform_instruction = "Create a Twitter thread (3-6 tweets). Each tweet must be under 280 chars. Focus on specific value nuggets."
        elif platform == 'linkedin':
            platform_instruction = "Create a LinkedIn post. Use line breaks for readability. Use a strong hook. Focus on storytelling and professional insights."
        elif platform == 'youtube':
            platform_instruction = "Create an engaging YouTube video title (hook) and a detailed, SEO-friendly video description (content)."
        elif platform == 'instagram':
            platform_instruction = "Create a vibrant Instagram caption. Use emojis creatively and keep the flow energetic. Focus on engagement."

        base_prompt = f"""
        You are an expert social media manager. I will provide you with content.
        Your task is to repurpose this into a high-quality post for {platform}.
        
        {platform_instruction}
        {voice_instruction}
        {custom_instruction}
        
        Return the result strictly as a valid JSON object with the following schema:
        {{
            "hook": "For YouTube: The video title. For others: The opening attention-grabber.",
            "content": "The main body of the post. For YouTube: The description.",
            "hashtags": ["tag1", "tag2"],
            "thread_posts": ["tweet 1", "tweet 2", ...] (Only for Twitter threads. Otherwise omit.)
        }}

        Here is the content:
        "{content[:20000]}..." (truncated)
        """
        
        return base_prompt
