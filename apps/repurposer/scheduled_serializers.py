"""
Serializers for scheduled posts.
"""
from rest_framework import serializers
from .models import ScheduledPost, RepurposedPost, BrandVoice


class ScheduledPostSerializer(serializers.ModelSerializer):
    """Serializer for ScheduledPost model."""
    post_title = serializers.SerializerMethodField()
    
    class Meta:
        model = ScheduledPost
        fields = [
            'id', 'post', 'post_title', 'prompt', 'platforms', 'brand_voice',
            'frequency', 'scheduled_time', 'status', 'is_active',
            'last_run', 'next_run', 'run_count', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_run', 'next_run', 'run_count', 'error_message', 'created_at', 'updated_at']
    
    def get_post_title(self, obj):
        if obj.post:
            return obj.post.hook or obj.post.source.title or "Untitled Post"
        return None
    
    def validate(self, data):
        # Must have either a post or a prompt
        if not data.get('post') and not data.get('prompt'):
            raise serializers.ValidationError(
                "You must provide either an existing 'post' or a 'prompt' for AI generation."
            )
        
        # If using prompt, must have platforms
        if data.get('prompt') and not data.get('platforms'):
            raise serializers.ValidationError(
                "When using a prompt, you must specify target platforms."
            )
        
        return data


class ScheduledPostCreateSerializer(serializers.Serializer):
    """Serializer for creating scheduled posts."""
    post_id = serializers.IntegerField(required=False, allow_null=True)
    prompt = serializers.CharField(required=False, allow_blank=True)
    platforms = serializers.ListField(
        child=serializers.ChoiceField(choices=RepurposedPost.Platform.choices),
        required=False,
        default=list
    )
    brand_voice_id = serializers.IntegerField(required=False, allow_null=True)
    frequency = serializers.ChoiceField(
        choices=ScheduledPost.Frequency.choices,
        default='once'
    )
    scheduled_time = serializers.DateTimeField()
    
    def validate(self, data):
        if not data.get('post_id') and not data.get('prompt'):
            raise serializers.ValidationError(
                "You must provide either 'post_id' or 'prompt'."
            )
        if data.get('prompt') and not data.get('platforms'):
            raise serializers.ValidationError(
                "When using prompt, you must specify platforms."
            )
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        
        post = None
        if validated_data.get('post_id'):
            post = RepurposedPost.objects.get(
                id=validated_data['post_id'],
                source__user=user
            )
        
        brand_voice = None
        if validated_data.get('brand_voice_id'):
            brand_voice = BrandVoice.objects.get(
                id=validated_data['brand_voice_id'],
                user=user
            )
        
        return ScheduledPost.objects.create(
            user=user,
            post=post,
            prompt=validated_data.get('prompt', ''),
            platforms=validated_data.get('platforms', []),
            brand_voice=brand_voice,
            frequency=validated_data.get('frequency', 'once'),
            scheduled_time=validated_data['scheduled_time']
        )
