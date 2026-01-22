"""
Content extraction service for various sources.
"""
import re
from typing import Tuple, Optional
from urllib.parse import urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup


class ContentExtractor:
    """Extract text content from various sources."""

    def extract_youtube(self, url: str) -> Tuple[str, str]:
        """
        Extract transcript from a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Tuple of (transcript_text, video_title)
        """
        video_id = self._get_youtube_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Get transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = ' '.join([entry['text'] for entry in transcript_list])
            
            # Get video title
            title = self._get_youtube_title(video_id)
            
            return transcript_text, title
            
        except Exception as e:
            raise Exception(f"Failed to extract YouTube transcript: {str(e)}")

    def extract_blog(self, url: str) -> Tuple[str, str]:
        """
        Extract main content from a blog article.
        
        Args:
            url: Blog article URL
            
        Returns:
            Tuple of (article_text, article_title)
        """
        try:
            response = httpx.get(url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # Try to find the title
            title = ''
            if soup.title:
                title = soup.title.string or ''
            elif soup.find('h1'):
                title = soup.find('h1').get_text(strip=True)
            
            # Try to find main content
            main_content = None
            
            # Look for common article containers
            for selector in ['article', 'main', '.post-content', '.entry-content', '.article-body', '#content']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.body
            
            if main_content:
                # Get text with some structure
                paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'li'])
                text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            return text, title
            
        except Exception as e:
            raise Exception(f"Failed to extract blog content: {str(e)}")

    def extract_pdf(self, file_path: str) -> Tuple[str, str]:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple of (pdf_text, filename)
        """
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_parts = []
                
                for page in reader.pages:
                    text_parts.append(page.extract_text())
                
                text = '\n\n'.join(text_parts)
                title = file_path.split('/')[-1].replace('.pdf', '')
                
                return text, title
                
        except Exception as e:
            raise Exception(f"Failed to extract PDF content: {str(e)}")

    def _get_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        parsed = urlparse(url)
        
        if parsed.hostname in ['www.youtube.com', 'youtube.com']:
            if parsed.path == '/watch':
                return parse_qs(parsed.query).get('v', [None])[0]
            elif parsed.path.startswith('/embed/'):
                return parsed.path.split('/')[2]
            elif parsed.path.startswith('/v/'):
                return parsed.path.split('/')[2]
        elif parsed.hostname == 'youtu.be':
            return parsed.path[1:]
        
        return None

    def _get_youtube_title(self, video_id: str) -> str:
        """Get YouTube video title using oEmbed API."""
        try:
            url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            response = httpx.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get('title', 'Untitled Video')
        except:
            pass
        return 'Untitled Video'
