"""
Celery tasks for scheduled and periodic posting.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_scheduled_posts():
    """
    Check for due scheduled posts and trigger publishing.
    This task runs every minute via Celery Beat.
    """
    from .models import ScheduledPost
    
    now = timezone.now()
    
    # Find posts due for publishing
    due_posts = ScheduledPost.objects.filter(
        is_active=True,
        status__in=['pending', 'active'],
        next_run__lte=now
    )
    
    logger.info(f"Found {due_posts.count()} scheduled posts due for publishing")
    
    for scheduled in due_posts:
        publish_scheduled_post.delay(scheduled.id)
    
    return f"Queued {due_posts.count()} posts for publishing"


@shared_task
def publish_scheduled_post(scheduled_post_id):
    """
    Publish a specific scheduled post to configured platforms.
    """
    from .models import ScheduledPost, RepurposedPost
    from apps.social_accounts.models import SocialAccount
    from apps.social_accounts.services import SocialMediaService
    
    try:
        scheduled = ScheduledPost.objects.get(id=scheduled_post_id)
    except ScheduledPost.DoesNotExist:
        logger.error(f"ScheduledPost {scheduled_post_id} not found")
        return
    
    logger.info(f"Processing scheduled post {scheduled.id}")
    
    try:
        # If we have an existing post, publish it
        if scheduled.post:
            post = scheduled.post
            result = _publish_post_to_platforms(scheduled.user, post)
        else:
            # Generate new content from prompt
            result = _generate_and_publish(scheduled)
        
        if result['success']:
            scheduled.run_count += 1
            scheduled.last_run = timezone.now()
            scheduled.error_message = ''
            
            # Calculate next run for recurring posts
            if scheduled.frequency == ScheduledPost.Frequency.ONCE:
                scheduled.status = ScheduledPost.Status.COMPLETED
                scheduled.is_active = False
            else:
                scheduled.next_run = _calculate_next_run(scheduled)
                scheduled.status = ScheduledPost.Status.ACTIVE
            
            scheduled.save()
            logger.info(f"Successfully published scheduled post {scheduled.id}")
        else:
            scheduled.status = ScheduledPost.Status.FAILED
            scheduled.error_message = result.get('error', 'Unknown error')
            scheduled.save()
            logger.error(f"Failed to publish scheduled post {scheduled.id}: {result.get('error')}")
            
    except Exception as e:
        scheduled.status = ScheduledPost.Status.FAILED
        scheduled.error_message = str(e)
        scheduled.save()
        logger.exception(f"Exception publishing scheduled post {scheduled.id}")


def _publish_post_to_platforms(user, post):
    """Helper to publish a post to its platform."""
    from apps.social_accounts.models import SocialAccount
    from apps.social_accounts.services import SocialMediaService
    
    # Get user's social account for this platform
    account = SocialAccount.objects.filter(
        user=user,
        platform=post.platform,
        is_active=True
    ).first()
    
    if not account:
        return {'success': False, 'error': f'No connected {post.platform} account found'}
    
    # Publish based on platform
    if post.platform == 'linkedin':
        return SocialMediaService.post_to_linkedin(
            account.access_token,
            account.platform_user_id,
            post.generated_content,
            media_file=post.media_file
        )
    elif post.platform == 'youtube':
        if not post.media_file:
            return {'success': False, 'error': 'Video file required for YouTube'}
        return SocialMediaService.post_to_youtube(
            account.access_token,
            title=post.hook or 'Scheduled Post',
            description=post.generated_content,
            video_file=post.media_file
        )
    elif post.platform == 'twitter':
        return SocialMediaService.post_to_twitter(
            account.access_token,
            post.generated_content,
            media_file=post.media_file
        )
    
    return {'success': False, 'error': f'Unsupported platform: {post.platform}'}


def _generate_and_publish(scheduled):
    """Generate AI content from prompt and publish."""
    from .services.ai_engine import AIEngine
    from .models import ContentSource, RepurposedPost
    
    if not scheduled.prompt:
        return {'success': False, 'error': 'No prompt provided for AI generation'}
    
    ai_engine = AIEngine()
    results = []
    
    for platform in scheduled.platforms:
        try:
            # Generate content
            generated = ai_engine.generate_post(
                content=scheduled.prompt,
                platform=platform,
                brand_voice=scheduled.brand_voice,
                user_prompt="Generate a fresh, engaging post based on this topic/prompt."
            )
            
            # Create a content source for tracking
            source = ContentSource.objects.create(
                user=scheduled.user,
                source_type='text',
                raw_text=scheduled.prompt,
                title=f"Scheduled AI Post - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                is_processed=True
            )
            
            # Create the post
            post = RepurposedPost.objects.create(
                source=source,
                platform=platform,
                brand_voice=scheduled.brand_voice,
                generated_content=generated.get('content', ''),
                hook=generated.get('hook', ''),
                hashtags=generated.get('hashtags', []),
                status='ready'
            )
            
            # Publish it
            result = _publish_post_to_platforms(scheduled.user, post)
            results.append(result)
            
            if result['success']:
                post.status = 'published'
                post.published_at = timezone.now()
                post.save()
                
        except Exception as e:
            results.append({'success': False, 'error': str(e)})
    
    # Check if at least one succeeded
    if any(r.get('success') for r in results):
        return {'success': True, 'results': results}
    return {'success': False, 'error': results[0].get('error') if results else 'Unknown error'}


def _calculate_next_run(scheduled):
    """Calculate the next run time for recurring posts."""
    from datetime import timedelta
    
    now = timezone.now()
    
    if scheduled.frequency == ScheduledPost.Frequency.DAILY:
        return now + timedelta(days=1)
    elif scheduled.frequency == ScheduledPost.Frequency.WEEKLY:
        return now + timedelta(weeks=1)
    elif scheduled.frequency == ScheduledPost.Frequency.MONTHLY:
        return now + timedelta(days=30)
    
    return None
