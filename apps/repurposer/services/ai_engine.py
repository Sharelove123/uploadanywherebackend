"""
AI Engine using Google Gemini for content generation.
"""
import json
from typing import Dict, List, Optional, Any

from django.conf import settings


class AIEngine:
    """AI-powered content generation using Google Gemini."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._client = None

    @property
    def client(self):
        """Lazy load the Gemini client."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    def generate_post(
        self,
        content: str,
        platform: str,
        brand_voice: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a social media post for a specific platform.
        
        Args:
            content: The original content to repurpose
            platform: Target platform (linkedin, twitter, instagram, youtube)
            brand_voice: Optional BrandVoice model instance
            
        Returns:
            Dict with generated content, hook, hashtags, etc.
        """
        # Build the prompt
        prompt = self._build_prompt(content, platform, brand_voice)
        
        try:
            response = self.client.generate_content(prompt)
            
            # Parse the response
            result = self._parse_response(response.text, platform)
            return result
            
        except Exception as e:
            # Return a fallback if AI fails
            return {
                'content': self._generate_fallback(content, platform),
                'hook': '',
                'hashtags': [],
                'thread_posts': [],
                'error': str(e)
            }

    def _build_prompt(
        self,
        content: str,
        platform: str,
        brand_voice: Optional[Any] = None
    ) -> str:
        """Build the AI prompt based on platform and voice."""
        
        platform_instructions = {
            'linkedin': """
Create a professional LinkedIn post that:
- Starts with a powerful hook (first line that grabs attention)
- Uses short paragraphs (1-2 sentences each)
- Includes a clear call-to-action
- Uses 3-5 relevant hashtags
- Maintains a professional yet conversational tone
- Is between 150-300 words
""",
            'twitter': """
Create a Twitter/X thread that:
- Has 5-7 tweets maximum
- First tweet is a hook that stops scrolling
- Each tweet is under 280 characters
- Uses engagement techniques (questions, bold claims)
- Ends with a call-to-action
- Include 2-3 relevant hashtags in the last tweet only
Format as a JSON array of tweet strings.
""",
            'instagram': """
Create an Instagram caption that:
- Starts with an attention-grabbing hook
- Tells a story or provides value
- Uses emojis strategically (not excessively)
- Ends with a question or call-to-action
- Is optimized for engagement
- Include 5-10 relevant hashtags at the end
""",
            'youtube': """
Create a YouTube Community post that:
- Is concise and engaging
- Encourages comments and discussion
- Can include a poll question if relevant
- Is conversational and authentic
- Under 500 characters
""",
            'newsletter': """
Create a newsletter section that:
- Has a compelling subject line
- Summarizes key insights
- Uses bullet points for readability
- Includes a clear takeaway
- Has a conversational tone
"""
        }
        
        voice_instruction = ""
        if brand_voice and brand_voice.generated_prompt:
            voice_instruction = f"\n\nWRITING STYLE:\n{brand_voice.generated_prompt}"
        elif brand_voice and brand_voice.sample_posts:
            voice_instruction = f"\n\nMATCH THIS WRITING STYLE (based on these examples):\n{brand_voice.sample_posts[:1000]}"
        
        prompt = f"""You are an expert social media content strategist.

ORIGINAL CONTENT TO REPURPOSE:
---
{content[:4000]}
---

PLATFORM: {platform.upper()}

{platform_instructions.get(platform, platform_instructions['linkedin'])}
{voice_instruction}

OUTPUT FORMAT:
Respond with valid JSON only:
{{
    "hook": "The attention-grabbing first line",
    "content": "The full post content",
    "hashtags": ["hashtag1", "hashtag2"],
    "thread_posts": ["tweet1", "tweet2"] // Only for Twitter
}}

Generate the post now:"""

        return prompt

    def _parse_response(self, response_text: str, platform: str) -> Dict[str, Any]:
        """Parse the AI response into structured data."""
        try:
            # Try to extract JSON from the response
            # Sometimes the model wraps it in markdown code blocks
            json_str = response_text
            
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0]
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0]
            
            data = json.loads(json_str.strip())
            
            return {
                'content': data.get('content', ''),
                'hook': data.get('hook', ''),
                'hashtags': data.get('hashtags', []),
                'thread_posts': data.get('thread_posts', []) if platform == 'twitter' else []
            }
            
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text
            return {
                'content': response_text,
                'hook': response_text.split('\n')[0] if response_text else '',
                'hashtags': [],
                'thread_posts': []
            }

    def _generate_fallback(self, content: str, platform: str) -> str:
        """Generate a simple fallback if AI fails."""
        # Take first 500 chars as a summary
        summary = content[:500]
        if len(content) > 500:
            summary += '...'
        
        return f"Key insights from this content:\n\n{summary}"

    def analyze_brand_voice(self, sample_posts: str) -> str:
        """
        Analyze sample posts to create a brand voice prompt.
        
        Args:
            sample_posts: Sample posts from the user
            
        Returns:
            Generated voice instructions for future posts
        """
        prompt = f"""Analyze these sample posts and describe the writing style:

{sample_posts}

Create detailed instructions for replicating this voice:
- Tone (formal, casual, humorous, etc.)
- Sentence structure preferences
- Common phrases or patterns
- Emoji usage
- Formatting preferences

Output a concise instruction set (under 200 words) that can be used to generate similar content:"""

        try:
            response = self.client.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Professional and engaging tone. Error analyzing: {str(e)}"

    def extract_key_insights(self, content: str) -> List[str]:
        """
        Extract key insights from content.
        
        Args:
            content: The original content
            
        Returns:
            List of key insight strings
        """
        prompt = f"""Extract the 5-7 most important insights from this content.
Return as a JSON array of strings.

Content:
{content[:3000]}

Output format: ["insight 1", "insight 2", ...]"""

        try:
            response = self.client.generate_content(prompt)
            text = response.text
            
            if '```' in text:
                text = text.split('```')[1].split('```')[0]
                if text.startswith('json'):
                    text = text[4:]
            
            return json.loads(text.strip())
        except:
            return []
