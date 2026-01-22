"""
Admin configuration for repurposer app.
"""
from django.contrib import admin
from .models import BrandVoice, ContentSource, RepurposedPost


@admin.register(BrandVoice)
class BrandVoiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__username']
    ordering = ['-created_at']


@admin.register(ContentSource)
class ContentSourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'source_type', 'is_processed', 'created_at']
    list_filter = ['source_type', 'is_processed', 'created_at']
    search_fields = ['title', 'user__username', 'source_url']
    ordering = ['-created_at']
    readonly_fields = ['raw_text', 'key_insights']


@admin.register(RepurposedPost)
class RepurposedPostAdmin(admin.ModelAdmin):
    list_display = ['id', 'platform', 'status', 'source', 'created_at', 'published_at']
    list_filter = ['platform', 'status', 'created_at']
    search_fields = ['source__title', 'generated_content']
    ordering = ['-created_at']
    readonly_fields = ['generated_content', 'hook', 'hashtags', 'thread_posts']
