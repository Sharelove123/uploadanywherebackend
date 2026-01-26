"""
Celery tasks for scheduled posting and recurring posts.
"""
import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.db import connection

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def publish_scheduled_posts(self):
    """
    Publish all posts that are scheduled for now or earlier.
    Runs every minute via Celery Beat.
    """
    from apps.repurposer.models import RepurposedPost
    from apps.social_accounts.models import SocialAccount
    from apps.social_accounts.services import SocialMediaService
    
    now = timezone.now()
    
    # Get all scheduled posts that are due
    scheduled_posts = RepurposedPost.objects.filter(
        status=RepurposedPost.Status.SCHEDULED,
        scheduled_for__lte=now
    ).select_related('source', 'source__user')
    
    published_count = 0
    failed_count = 0
    
    for post in scheduled_posts:
        try:
            user = post.source.user
            
            # Get connected social account for this platform
            account = SocialAccount.objects.filter(
                user=user,
                platform=post.platform,
                is_active=True
            ).first()
            
            if not account:
                post.status = RepurposedPost.Status.FAILED
                post.error_message = f"No connected {post.get_platform_display()} account"
                post.save()
                failed_count += 1
                continue
            
            # Publish based on platform
            result = None
            if post.platform == 'linkedin':
                result = SocialMediaService.post_to_linkedin(
                    account.access_token,
                    account.platform_user_id,
                    post.generated_content
                )
            elif post.platform == 'twitter':
                text = post.generated_content
                if post.thread_posts:
                    text = post.thread_posts[0] if post.thread_posts else text
                result = SocialMediaService.post_to_twitter(
                    account.access_token,
                    text,
                    media_file=post.media_file if post.media_file else None
                )
            elif post.platform == 'youtube':
                result = SocialMediaService.post_to_youtube(
                    account.access_token,
                    title=post.hook or "Scheduled Post",
                    description=post.generated_content,
                    video_file=post.media_file
                )
            
            if result and result.get('success'):
                post.status = RepurposedPost.Status.PUBLISHED
                post.published_at = timezone.now()
                post.platform_post_id = str(result.get('id', ''))
                post.platform_post_url = result.get('url', '')
                published_count += 1
            else:
                post.status = RepurposedPost.Status.FAILED
                post.error_message = result.get('error', 'Unknown error') if result else 'No result from service'
                failed_count += 1
            
            post.save()
            
        except Exception as e:
            logger.error(f"Failed to publish scheduled post {post.id}: {str(e)}")
            post.status = RepurposedPost.Status.FAILED
            post.error_message = str(e)
            post.save()
            failed_count += 1
    
    logger.info(f"Scheduled posting complete: {published_count} published, {failed_count} failed")
    return {'published': published_count, 'failed': failed_count}


@shared_task(bind=True)
def create_recurring_posts(self):
    """
    Create new scheduled posts from recurring post templates.
    Runs daily at 00:05 UTC via Celery Beat.
    """
    from apps.repurposer.models import RepurposedPost
    
    now = timezone.now()
    today = now.date()
    
    # Get all active recurring posts
    recurring_posts = RepurposedPost.objects.filter(
        is_recurring=True,
        is_recurring_active=True,
        status=RepurposedPost.Status.READY
    ).select_related('source')
    
    created_count = 0
    
    for template in recurring_posts:
        try:
            should_create = False
            next_schedule = None
            
            if template.recurrence_pattern == 'daily':
                # Daily: always create for today
                should_create = True
                next_schedule = datetime.combine(
                    today, 
                    template.recurrence_time or datetime.min.time()
                )
                
            elif template.recurrence_pattern == 'weekly':
                # Weekly: check if today is in recurrence_days (0=Mon, 6=Sun)
                if today.weekday() in template.recurrence_days:
                    should_create = True
                    next_schedule = datetime.combine(
                        today, 
                        template.recurrence_time or datetime.min.time()
                    )
                    
            elif template.recurrence_pattern == 'monthly':
                # Monthly: check if today's day matches
                if today.day in template.recurrence_days:
                    should_create = True
                    next_schedule = datetime.combine(
                        today, 
                        template.recurrence_time or datetime.min.time()
                    )
            
            # Check if we already created one today
            if should_create and template.last_recurrence_created:
                if template.last_recurrence_created.date() == today:
                    should_create = False
            
            if should_create and next_schedule:
                # Make timezone aware
                next_schedule = timezone.make_aware(next_schedule)
                
                # Create a new scheduled post (copy of template)
                new_post = RepurposedPost.objects.create(
                    source=template.source,
                    platform=template.platform,
                    brand_voice=template.brand_voice,
                    generated_content=template.generated_content,
                    hook=template.hook,
                    hashtags=template.hashtags,
                    thread_posts=template.thread_posts,
                    status=RepurposedPost.Status.SCHEDULED,
                    scheduled_for=next_schedule,
                    media_file=template.media_file,
                    # Don't copy recurring settings - this is a one-time scheduled post
                )
                
                # Update template's last_recurrence_created
                template.last_recurrence_created = now
                template.save(update_fields=['last_recurrence_created'])
                
                created_count += 1
                logger.info(f"Created recurring post {new_post.id} from template {template.id}")
                
        except Exception as e:
            logger.error(f"Failed to create recurring post from template {template.id}: {str(e)}")
    
    logger.info(f"Recurring post creation complete: {created_count} posts created")
    return {'created': created_count}
