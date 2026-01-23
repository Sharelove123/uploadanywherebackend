
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

            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
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
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.title.string if soup.title else "Blog Article"
            
            # Simple heuristic: get all p tags
            paragraphs = soup.find_all('p')
            text = "\n\n".join([p.get_text() for p in paragraphs])
            return text, title
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
