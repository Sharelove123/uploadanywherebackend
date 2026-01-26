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
                account.access_token,
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
            if not post.media_file:
                return Response({'error': 'Image file is required for Instagram.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Instagram requires a publicly accessible URL
            image_url = request.build_absolute_uri(post.media_file.url)
            
            # Check if URL is localhost - Meta APIs cannot access localhost
            if any(x in image_url.lower() for x in ['localhost', '127.0.0.1', 'lvh.me', '0.0.0.0']):
                return Response({
                    'error': 'Instagram requires publicly accessible image URLs. Cannot post from localhost. Please deploy your backend to a public server (like Render) first, or use a public image hosting service.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = SocialMediaService.post_to_instagram(
                account.access_token,
                account.platform_user_id,
                caption=post.generated_content,
                image_url=image_url
            )
        elif post.platform == SocialAccount.Platform.FACEBOOK:
            # Facebook Page posting - uses Page Access Token stored during connection
            image_url = None
            if post.media_file:
                image_url = request.build_absolute_uri(post.media_file.url)
                
                # Check if URL is localhost - Meta APIs cannot access localhost
                if any(x in image_url.lower() for x in ['localhost', '127.0.0.1', 'lvh.me', '0.0.0.0']):
                    return Response({
                        'error': 'Facebook requires publicly accessible image URLs. Cannot post from localhost. Please deploy your backend to a public server (like Render) first, or use a public image hosting service.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            result = SocialMediaService.post_to_facebook(
                account.access_token,  # This is the Page Access Token
                account.platform_user_id,  # This is the Page ID
                message=post.generated_content,
                image_url=image_url
            )
            
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

    def post(self, request):
        serializer = RepurposeRequestSerializer(
            data=request.data,
            context={'request': request}
        )
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
        if 'youtube.com' in source_url or 'youtu.be' in source_url:
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
                    source_url=content_source.source_url
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
