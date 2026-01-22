"""
Serializers for Social Accounts app.
"""
from rest_framework import serializers
from .models import SocialAccount, PostingLog


class SocialAccountSerializer(serializers.ModelSerializer):
    """Serializer for SocialAccount model."""
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    is_token_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = SocialAccount
        fields = [
            'id', 'platform', 'platform_display',
            'platform_username', 'platform_name', 'profile_url', 'avatar_url',
            'is_active', 'is_token_expired', 'last_used_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'platform', 'platform_username', 'platform_name',
            'profile_url', 'avatar_url', 'last_used_at',
            'created_at', 'updated_at'
        ]


class PostingLogSerializer(serializers.ModelSerializer):
    """Serializer for PostingLog model."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    platform = serializers.CharField(source='social_account.platform', read_only=True)

    class Meta:
        model = PostingLog
        fields = [
            'id', 'platform', 'status', 'status_display',
            'error_message', 'created_at'
        ]


class OAuthCallbackSerializer(serializers.Serializer):
    """Serializer for OAuth callback handling."""
    code = serializers.CharField(required=True)
    state = serializers.CharField(required=False)
