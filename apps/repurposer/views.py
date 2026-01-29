"""
API Views for Content Repurposer app.
"""
from rest_framework import generics, status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import BrandVoice, ContentSource, RepurposedPost
from .serializers import (
    BrandVoiceSerializer,
    ContentSourceSerializer,
    ContentSourceListSerializer,
    RepurposedPostSerializer,
    RepurposeRequestSerializer,
    PublishPostSerializer
)


class BrandVoiceViewSet(viewsets.ModelViewSet):
    """CRUD operations for Brand Voices."""
    serializer_class = BrandVoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BrandVoice.objects.filter(user=self.request.user)


class ContentSourceViewSet(viewsets.ModelViewSet):
    """CRUD operations for Content Sources."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ContentSource.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return ContentSourceListSerializer
        return ContentSourceSerializer


class RepurposedPostViewSet(viewsets.ModelViewSet):
    """CRUD operations for Repurposed Posts."""
    serializer_class = RepurposedPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RepurposedPost.objects.filter(
            source__user=self.request.user
        ).select_related('source', 'brand_voice')

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a post to social media."""
        from apps.social_accounts.models import SocialAccount
        from apps.social_accounts.services import SocialMediaService
        from django.utils import timezone

        post = self.get_object()
        serializer = PublishPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 1. Get Social Account
        account_id = serializer.validated_data.get('social_account_id')
        if account_id:
            try:
                account = SocialAccount.objects.get(id=account_id, user=request.user, is_active=True)
            except SocialAccount.DoesNotExist:
                return Response({'error': 'Invalid social account.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Auto-select
            account = SocialAccount.objects.filter(
                user=request.user, 
                platform=post.platform, 
                is_active=True
            ).first()
            if not account:
                return Response({'error': f'No connected {post.get_platform_display()} account found.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Call Service
        result = {'success': False, 'error': 'Unknown platform'}
        
        if post.platform == SocialAccount.Platform.LINKEDIN:
            result = SocialMediaService.post_to_linkedin(
                account.access_token, 
                account.platform_user_id, 
                post.generated_content,
                media_file=post.media_file
            )
        elif post.platform == SocialAccount.Platform.TWITTER:
            result = SocialMediaService.post_to_twitter(
                account,
                post.generated_content,
                media_file=post.media_file
            )
        elif post.platform == SocialAccount.Platform.YOUTUBE:
            if not post.media_file:
                return Response({'error': 'Video file is required for YouTube.'}, status=status.HTTP_400_BAD_REQUEST)
            
            result = SocialMediaService.post_to_youtube(
                account.access_token,
                title=post.hook or f"Video by {request.user.username}", # Fallback title
                description=post.generated_content,
                video_file=post.media_file
            )
        elif post.platform == SocialAccount.Platform.INSTAGRAM:
            return Response({
                'error': 'Direct publishing to Instagram is currently disabled. You can copy the generated content and post manually.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        elif post.platform == SocialAccount.Platform.FACEBOOK:
            return Response({
                'error': 'Direct publishing to Facebook is currently disabled. You can copy the generated content and post manually.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # 3. Handle Result
        if result['success']:
            post.status = RepurposedPost.Status.PUBLISHED
            post.published_at = timezone.now()
            post.platform_post_id = str(result.get('id', ''))
            post.platform_post_url = result.get('url', '')
            post.save()
            
            return Response({
                'message': 'Post published successfully.',
                'post': RepurposedPostSerializer(post).data
            })
        else:
            post.status = RepurposedPost.Status.FAILED
            post.error_message = result.get('error', 'Unknown error')
            post.save()
            return Response({
                'error': f"Publishing failed: {result.get('error')}",
                'post': RepurposedPostSerializer(post).data
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate content for this post."""
        post = self.get_object()
        
        if not request.user.can_repurpose():
            return Response(
                {'error': 'You have reached your monthly repurpose limit.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response({
            'message': 'Content regenerated.',
            'post': RepurposedPostSerializer(post).data
        })


class RepurposeView(APIView):
    """Main endpoint to submit content for repurposing."""
    permission_classes = [permissions.IsAuthenticated]
    # Support file uploads
    from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        # Debug Logging for Payload
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Repurpose Request Data: {request.data}")
        logger.info(f"Repurpose Request Files: {request.FILES}")

        data = request.data.copy()
        
        # Handle 'platforms' being sent as a JSON string (common in FormData)
        if 'platforms' in data and isinstance(data['platforms'], str):
            try:
                import json
                data['platforms'] = json.loads(data['platforms'])
            except:
                pass

        serializer = RepurposeRequestSerializer(
            data=data,
            context={'request': request}
        )
        if not serializer.is_valid():
            logger.error(f"Repurpose Validation Error: {serializer.errors}")
            # Format error for frontend
            error_msg = "Validation Error: " + ", ".join([f"{k}: {v[0]}" for k, v in serializer.errors.items()])
            return Response({'error': error_msg, 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Check user limits
        if not user.can_repurpose():
            return Response(
                {'error': 'You have reached your monthly repurpose limit. Upgrade to continue.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = serializer.validated_data
        
        # Determine source type
        source_url = data.get('source_url', '')
        source_file = data.get('source_file')
        
        if source_file:
            source_type = ContentSource.SourceType.PDF
        elif 'youtube.com' in source_url or 'youtu.be' in source_url:
            source_type = ContentSource.SourceType.YOUTUBE
        elif source_url:
            source_type = ContentSource.SourceType.BLOG
        else:
            source_type = ContentSource.SourceType.TEXT
        
        # Create content source
        content_source = ContentSource.objects.create(
            user=user,
            source_type=source_type,
            source_url=source_url or None,
            raw_text=data.get('raw_text', ''),
            title=data.get('title', '')
        )

        
        # Get brand voice if specified
        brand_voice = None
        if data.get('brand_voice_id'):
            brand_voice = BrandVoice.objects.get(id=data['brand_voice_id'])
        
        # Create pending posts for each platform
        platforms = data['platforms']
        posts = []
        for platform in platforms:
            post = RepurposedPost.objects.create(
                source=content_source,
                platform=platform,
                brand_voice=brand_voice,
                status=RepurposedPost.Status.PENDING
            )
            posts.append(post)
        
        # Try to process content (AI services may not be available)
        try:
            from .services.ai_engine import AIEngine
            from .services.extractor import ContentExtractor
            
            # Extract content
            extractor = ContentExtractor()
            if source_type == ContentSource.SourceType.YOUTUBE:
                extracted_text, title = extractor.extract_youtube(source_url)
            elif source_type == ContentSource.SourceType.BLOG:
                extracted_text, title = extractor.extract_blog(source_url)
            elif source_type == ContentSource.SourceType.PDF and source_file:
                extracted_text = extractor.extract_pdf_content(source_file)
                title = data.get('title', '') or source_file.name.rsplit('.', 1)[0] or 'Uploaded Document'
            else:
                extracted_text = content_source.raw_text
                title = data.get('title', 'Untitled')

            
            content_source.raw_text = extracted_text
            content_source.title = title or content_source.title or 'Untitled'
            content_source.save()
            
            # Generate content for each platform
            ai_engine = AIEngine()
            for post in posts:
                generated = ai_engine.generate_post(
                    content=extracted_text,
                    platform=post.platform,
                    brand_voice=brand_voice,
                    source_url=content_source.source_url,
                    user_prompt=data.get('user_prompt')
                )
                post.generated_content = generated.get('content', '')
                post.hook = generated.get('hook', '')
                post.hashtags = generated.get('hashtags') or []
                post.thread_posts = generated.get('thread_posts') or []
                post.status = RepurposedPost.Status.READY
                post.save()
            
            content_source.is_processed = True
            content_source.save()
            
            # Increment user usage
            user.increment_usage()
            
        except ImportError as e:
            # AI services not available (packages not installed)
            content_source.processing_error = f'AI services not available: {str(e)}'
            content_source.save()
            
            for post in posts:
                post.status = RepurposedPost.Status.FAILED
                post.error_message = 'AI packages not installed. Please install: pip install httpx beautifulsoup4 google-generativeai youtube-transcript-api PyPDF2'
                post.save()
            
            return Response({
                'message': 'Content source created but AI processing unavailable. Install required packages.',
                'source': ContentSourceSerializer(content_source).data,
                'posts': RepurposedPostSerializer(posts, many=True).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            content_source.processing_error = str(e)
            content_source.save()
            
            for post in posts:
                post.status = RepurposedPost.Status.FAILED
                post.error_message = str(e)
                post.save()
            
            return Response({
                'error': f'Failed to process content: {str(e)}',
                'source_id': content_source.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'Content repurposed successfully.',
            'source': ContentSourceSerializer(content_source).data,
            'posts': RepurposedPostSerializer(posts, many=True).data
        }, status=status.HTTP_201_CREATED)


class ScheduledPostViewSet(viewsets.ModelViewSet):
    """CRUD operations for Scheduled Posts."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        from .scheduled_serializers import ScheduledPostSerializer, ScheduledPostCreateSerializer
        if self.action == 'create':
            return ScheduledPostCreateSerializer
        return ScheduledPostSerializer
    
    def get_queryset(self):
        from .models import ScheduledPost
        return ScheduledPost.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a scheduled post."""
        scheduled = self.get_object()
        scheduled.is_active = False
        scheduled.status = 'paused'
        scheduled.save()
        from .scheduled_serializers import ScheduledPostSerializer
        return Response({
            'message': 'Scheduled post paused.',
            'scheduled_post': ScheduledPostSerializer(scheduled).data
        })
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused scheduled post."""
        scheduled = self.get_object()
        scheduled.is_active = True
        scheduled.status = 'active'
        scheduled.save()
        from .scheduled_serializers import ScheduledPostSerializer
        return Response({
            'message': 'Scheduled post resumed.',
            'scheduled_post': ScheduledPostSerializer(scheduled).data
        })
