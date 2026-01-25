"""
Core models for the Content Repurposer app.
"""
from django.db import models
from django.conf import settings


class BrandVoice(models.Model):
    """Stores the user's custom writing style/tone."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='brand_voices'
    )
    name = models.CharField(max_length=100)  # e.g., "Professional", "Casual"
    description = models.TextField(blank=True, help_text="Describe this voice style")
    sample_posts = models.TextField(help_text="3-5 sample posts to learn tone from")
    generated_prompt = models.TextField(blank=True, help_text="AI-generated style instructions")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class ContentSource(models.Model):
    """The original content (YouTube, Blog, PDF, or raw text)."""
    
    class SourceType(models.TextChoices):
        YOUTUBE = 'youtube', 'YouTube Video'
        BLOG = 'blog', 'Blog Article'
        PDF = 'pdf', 'PDF Document'
        TEXT = 'text', 'Raw Text'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_sources'
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_url = models.URLField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True)
    
    # Extracted content
    raw_text = models.TextField(blank=True, help_text="Extracted or pasted text")
    key_insights = models.JSONField(default=list, blank=True, help_text="AI-extracted key points")
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Content Source'
        verbose_name_plural = 'Content Sources'

    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.get_source_type_display()})"


class RepurposedPost(models.Model):
    """The AI-generated output for a specific platform."""
    
    class Platform(models.TextChoices):
        LINKEDIN = 'linkedin', 'LinkedIn'
        TWITTER = 'twitter', 'X (Twitter)'
        INSTAGRAM = 'instagram', 'Instagram'
        YOUTUBE = 'youtube', 'YouTube Community'
        NEWSLETTER = 'newsletter', 'Newsletter'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready'
        SCHEDULED = 'scheduled', 'Scheduled'
        PUBLISHED = 'published', 'Published'
        FAILED = 'failed', 'Failed'

    source = models.ForeignKey(
        ContentSource,
        on_delete=models.CASCADE,
        related_name='repurposed_posts'
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    brand_voice = models.ForeignKey(
        BrandVoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Generated content
    generated_content = models.TextField(blank=True)
    hook = models.CharField(max_length=500, blank=True, help_text="Attention-grabbing first line")
    hashtags = models.JSONField(default=list, blank=True)
    
    # For Twitter threads
    thread_posts = models.JSONField(default=list, blank=True, help_text="List of thread posts")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    
    # Publishing info
    scheduled_for = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    platform_post_id = models.CharField(max_length=255, blank=True, help_text="ID from platform after posting")
    platform_post_url = models.URLField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Repurposed Post'
        verbose_name_plural = 'Repurposed Posts'

    def __str__(self):
        return f"{self.get_platform_display()} post from {self.source}"
    
    @property
    def is_thread(self) -> bool:
        """Check if this is a Twitter thread."""
        return self.platform == self.Platform.TWITTER and len(self.thread_posts) > 1
    
    @property
    def content_preview(self) -> str:
        """Get a preview of the generated content."""
        content = self.generated_content or ''
        return content[:150] + '...' if len(content) > 150 else content

    # Media attachment
    media_file = models.FileField(upload_to='post_media/', blank=True, null=True, help_text="Image or video file to attach")

