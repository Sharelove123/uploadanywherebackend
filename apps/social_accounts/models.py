"""
Models for social media account connections and OAuth tokens.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class SocialAccount(models.Model):
    """Connected social media accounts."""
    
    class Platform(models.TextChoices):
        LINKEDIN = 'linkedin', 'LinkedIn'
        TWITTER = 'twitter', 'X (Twitter)'
        INSTAGRAM = 'instagram', 'Instagram'
        YOUTUBE = 'youtube', 'YouTube'
        FACEBOOK = 'facebook', 'Facebook'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='social_accounts'
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    
    # Platform-specific identifiers
    platform_user_id = models.CharField(max_length=255)
    platform_username = models.CharField(max_length=255, blank=True)
    platform_name = models.CharField(max_length=255, blank=True)  # Display name
    profile_url = models.URLField(blank=True)
    avatar_url = models.URLField(blank=True)
    
    # OAuth tokens (encrypted in production)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'platform', 'platform_user_id']
        verbose_name = 'Social Account'
        verbose_name_plural = 'Social Accounts'

    def __str__(self):
        return f"{self.user.username} - {self.get_platform_display()} (@{self.platform_username})"
    
    @property
    def is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        if not self.token_expires_at:
            return False
        return timezone.now() >= self.token_expires_at
    
    def mark_used(self):
        """Update last used timestamp."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])


class PostingLog(models.Model):
    """Log of all posting attempts to social platforms."""
    
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        RATE_LIMITED = 'rate_limited', 'Rate Limited'

    social_account = models.ForeignKey(
        SocialAccount,
        on_delete=models.CASCADE,
        related_name='posting_logs'
    )
    repurposed_post = models.ForeignKey(
        'repurposer.RepurposedPost',
        on_delete=models.CASCADE,
        related_name='posting_logs'
    )
    
    status = models.CharField(max_length=20, choices=Status.choices)
    platform_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Posting Log'
        verbose_name_plural = 'Posting Logs'

    def __str__(self):
        return f"{self.social_account.platform} - {self.status} - {self.created_at}"
