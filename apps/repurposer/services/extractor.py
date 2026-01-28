
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
            error_str = str(e)
            logger.error(f"Error extracting YouTube transcript: {error_str}")
            
            # Check for IP blocking errors
            if 'blocked' in error_str.lower() or 'ip' in error_str.lower() or 'cloud' in error_str.lower():
                raise ValueError(
                    "YouTube is blocking requests from our server. "
                    "Workaround: Open the YouTube video, click '...' → 'Show transcript', "
                    "copy the text, and paste it in the 'Text' tab instead."
                )
            raise e

    @staticmethod
    def extract_blog(url: str) -> tuple[str, str]:
        """Extracts main text content and title from a blog article URL."""
        try:
            import random
            import time
            
            # Check if it's a Medium URL - these require special handling
            is_medium = 'medium.com' in url.lower()
            
            # List of user agents to rotate
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            ]
            
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/search?q=blog",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
            
            # Use session for better cookie handling
            session = requests.Session()
            
            # Add delay for Medium to look more human
            if is_medium:
                time.sleep(random.uniform(1, 2))
            
            # Try up to 3 times with different user agents
            last_error = None
            for attempt in range(3):
                try:
                    if attempt > 0:
                        headers["User-Agent"] = random.choice(user_agents)
                        time.sleep(random.uniform(1, 3))
                    
                    response = session.get(url, headers=headers, timeout=20, verify=True, allow_redirects=True)
                    response.raise_for_status()
                    break
                except requests.exceptions.HTTPError as e:
                    last_error = e
                    if response.status_code == 403 and attempt < 2:
                        continue  # Retry with different user agent
                    raise
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.title.string if soup.title else "Blog Article"
            
            # Try to find article content first (works better for Medium, blogs)
            article = soup.find('article')
            if article:
                paragraphs = article.find_all('p')
            else:
                # Fallback: look for main content div
                main = soup.find('main') or soup.find('div', {'class': ['content', 'post-content', 'article-content', 'story-content']})
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
            
            # Check if we got meaningful content
            if not text or len(text) < 100:
                raise ValueError(
                    "Could not extract article content. The page may be behind a paywall, "
                    "require login, or block automated access. Try copying the text directly instead."
                )
                    
            return text, title
        except requests.exceptions.Timeout:
            logger.error(f"Timeout extracting blog content from: {url}")
            raise ValueError("The website took too long to respond. Please try again.")
        except requests.exceptions.HTTPError as e:
            if '403' in str(e):
                logger.error(f"403 Forbidden extracting blog from: {url}")
                raise ValueError(
                    "This website blocks automated access (403 Forbidden). "
                    "Please copy the article text and paste it in the 'Text' tab instead."
                )
            logger.error(f"HTTP error extracting blog content: {str(e)}")
            raise ValueError(f"Could not access the URL: {str(e)}")
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
