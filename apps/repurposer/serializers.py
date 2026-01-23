"""
Serializers for Content Repurposer app.
"""
from rest_framework import serializers
from .models import BrandVoice, ContentSource, RepurposedPost


class BrandVoiceSerializer(serializers.ModelSerializer):
    """Serializer for BrandVoice model."""
    
    class Meta:
        model = BrandVoice
        fields = [
            'id', 'name', 'description', 'sample_posts',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class RepurposedPostSerializer(serializers.ModelSerializer):
    """Serializer for RepurposedPost model."""
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    brand_voice_name = serializers.CharField(source='brand_voice.name', read_only=True)

    class Meta:
        model = RepurposedPost
        fields = [
            'id', 'platform', 'platform_display', 'brand_voice', 'brand_voice_name',
            'generated_content', 'hook', 'hashtags', 'thread_posts',
            'status', 'status_display', 'error_message',
            'scheduled_for', 'published_at', 'platform_post_url',
            'content_preview', 'is_thread',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'generated_content', 'hook', 'hashtags', 'thread_posts',
            'status', 'error_message', 'published_at', 'platform_post_url',
            'created_at', 'updated_at'
        ]


class ContentSourceSerializer(serializers.ModelSerializer):
    """Serializer for ContentSource model."""
    repurposed_posts = RepurposedPostSerializer(many=True, read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = ContentSource
        fields = [
            'id', 'source_type', 'source_type_display', 'source_url', 'title',
            'raw_text', 'key_insights', 'is_processed', 'processing_error',
            'repurposed_posts', 'posts_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'title', 'raw_text', 'key_insights',
            'is_processed', 'processing_error',
            'created_at', 'updated_at'
        ]

    def get_posts_count(self, obj) -> int:
        return obj.repurposed_posts.count()


class ContentSourceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing content sources."""
    repurposed_posts = RepurposedPostSerializer(many=True, read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = ContentSource
        fields = [
            'id', 'source_type', 'source_type_display', 'source_url', 'title',
            'is_processed', 'posts_count', 'created_at', 'repurposed_posts'
        ]

    def get_posts_count(self, obj) -> int:
        return obj.repurposed_posts.count()


class RepurposeRequestSerializer(serializers.Serializer):
    """Input serializer for the main repurpose endpoint."""
    source_url = serializers.URLField(required=False, allow_blank=True)
    raw_text = serializers.CharField(required=False, allow_blank=True)
    platforms = serializers.MultipleChoiceField(
        choices=RepurposedPost.Platform.choices,
        required=True
    )
    brand_voice_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, data):
        if not data.get('source_url') and not data.get('raw_text'):
            raise serializers.ValidationError(
                "You must provide either a 'source_url' or 'raw_text'."
            )
        
        # Validate brand voice belongs to user
        brand_voice_id = data.get('brand_voice_id')
        if brand_voice_id:
            user = self.context['request'].user
            if not BrandVoice.objects.filter(id=brand_voice_id, user=user).exists():
                raise serializers.ValidationError({
                    'brand_voice_id': "Invalid brand voice."
                })
        
        return data


class PublishPostSerializer(serializers.Serializer):
    """Serializer for publishing a post."""
    social_account_id = serializers.IntegerField(required=True)
    schedule_for = serializers.DateTimeField(required=False, allow_null=True)
