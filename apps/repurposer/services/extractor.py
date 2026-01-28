
import logging
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io

logger = logging.getLogger(__name__)

class ContentExtractor:
    """Service to extract text content from various sources."""

    @staticmethod
    def extract_youtube(url: str) -> tuple[str, str]:
        """Extracts transcript and title from a YouTube video URL."""
        try:
            video_id = ContentExtractor._get_youtube_video_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            # Use new instance-based API (youtube-transcript-api >= 0.6.3)
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id)
            # Convert to raw data format for compatibility
            transcript_list = transcript.to_raw_data()
            full_transcript = " ".join([item['text'] for item in transcript_list])
            
            # TODO: Fetch actual title using an API or scraping
            title = f"YouTube Video ({video_id})"
            
            return full_transcript, title
        except Exception as e:
            logger.error(f"Error extracting YouTube transcript: {str(e)}")
            raise e

    @staticmethod
    def extract_blog(url: str) -> tuple[str, str]:
        """Extracts main text content and title from a blog article URL."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/",
                "Upgrade-Insecure-Requests": "1",
            }
            # Use session for better cookie handling
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=15, verify=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.title.string if soup.title else "Blog Article"
            
            # Try to find article content first (works better for Medium, blogs)
            article = soup.find('article')
            if article:
                paragraphs = article.find_all('p')
            else:
                # Fallback: look for main content div
                main = soup.find('main') or soup.find('div', {'class': ['content', 'post-content', 'article-content']})
                if main:
                    paragraphs = main.find_all('p')
                else:
                    # Last resort: all paragraphs
                    paragraphs = soup.find_all('p')
            
            # Filter out short paragraphs (likely navigation/ads)
            text_parts = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50]
            text = "\n\n".join(text_parts)
            
            if not text:
                # If no paragraphs found, try getting all text from body
                body = soup.find('body')
                if body:
                    text = body.get_text(separator='\n', strip=True)
                    
            return text, title
        except requests.exceptions.Timeout:
            logger.error(f"Timeout extracting blog content from: {url}")
            raise ValueError("The website took too long to respond. Please try again.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error extracting blog content: {str(e)}")
            raise ValueError(f"Could not access the URL: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting blog content: {str(e)}")
            raise e


    @staticmethod
    def extract_pdf_content(file_obj) -> str:
        """Extracts text from a PDF file object."""
        try:
            reader = PyPDF2.PdfReader(file_obj)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF content: {str(e)}")
            raise e

    @staticmethod
    def _get_youtube_video_id(url: str) -> str:
        """Parses YouTube video ID from URL."""
        parsed = urlparse(url)
        if parsed.hostname == 'youtu.be':
            return parsed.path[1:]
        if parsed.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed.path == '/watch':
                p = parse_qs(parsed.query)
                return p['v'][0]
            if parsed.path[:7] == '/embed/':
                return parsed.path.split('/')[2]
            if parsed.path[:3] == '/v/':
                return parsed.path.split('/')[2]
        return None
