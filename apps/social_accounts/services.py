
import requests
import json
import logging

logger = logging.getLogger(__name__)

class SocialMediaService:
    @staticmethod
    def post_to_linkedin(access_token, person_id, text, media_file=None):
        """
        Post text to LinkedIn profile using UGC API.
        Supports image upload.
        """
        # Ensure person_id is a URN
        if not person_id.startswith('urn:li:'):
            author_urn = f"urn:li:person:{person_id}"
        else:
            author_urn = person_id
            
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

        # Handle Media Upload
        asset_urn = None
        if media_file:
            try:
                # 1. Register Upload
                register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
                register_payload = {
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": author_urn,
                        "serviceRelationships": [{
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }]
                    }
                }
                reg_response = requests.post(register_url, headers=headers, json=register_payload)
                
                if reg_response.status_code == 200:
                    reg_data = reg_response.json()
                    upload_url = reg_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                    asset_urn = reg_data['value']['asset']
                    
                    # 2. Upload Binary
                    # Reset pointer just in case
                    if hasattr(media_file, 'seek'):
                        media_file.seek(0)
                    
                    # Use a binary header for upload
                    upload_headers = {'Authorization': f'Bearer {access_token}'}
                    upload_res = requests.put(upload_url, headers=upload_headers, data=media_file)
                    
                    if upload_res.status_code != 201:
                         logger.error(f"LinkedIn binary upload failed: {upload_res.text}")
                         # Proceed without image or fail? Let's fail for now to be clear
                         return {'success': False, 'error': f"Image upload failed: {upload_res.text}"}
                else:
                    logger.error(f"LinkedIn upload registration failed: {reg_response.text}")
                    return {'success': False, 'error': f"Image registration failed: {reg_response.text}"}
            except Exception as e:
                logger.error(f"LinkedIn media upload exception: {str(e)}")
                return {'success': False, 'error': f"Media upload error: {str(e)}"}

        # Construct Post Payload
        url = "https://api.linkedin.com/v2/ugcPosts"
        
        share_content = {
            "shareCommentary": {
                "text": text
            },
            "shareMediaCategory": "NONE"
        }

        if asset_urn:
            share_content["shareMediaCategory"] = "IMAGE"
            share_content["media"] = [{
                "status": "READY",
                "description": {"text": "Image"},
                "media": asset_urn,
                "title": {"text": "Image"}
            }]

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": share_content
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            data = response.json()
            return {
                'success': True,
                'id': data.get('id'),
                'url': f"https://www.linkedin.com/feed/update/{data.get('id')}/" 
            }
        else:
            logger.error(f"LinkedIn posting failed: {response.text}")
            return {
                'success': False,
                'error': response.text
            }

    @staticmethod
    def refresh_twitter_token(social_account):
        """
        Refreshes the Twitter OAuth 2.0 token.
        """
        import base64
        from django.conf import settings
        from django.utils import timezone
        
        client_id = getattr(settings, 'TWITTER_CLIENT_ID', settings.TWITTER_API_KEY)
        client_secret = getattr(settings, 'TWITTER_CLIENT_SECRET', settings.TWITTER_API_SECRET)
        
        if not social_account.refresh_token:
            logger.error(f"Cannot refresh Twitter token for {social_account.user}: No refresh token.")
            return False

        url = 'https://api.twitter.com/2/oauth2/token'
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': social_account.refresh_token,
            'client_id': client_id,
        }
        
        try:
            response = requests.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                social_account.access_token = token_data['access_token']
                if 'refresh_token' in token_data:
                    social_account.refresh_token = token_data['refresh_token']
                
                # Update expiration
                expires_in = token_data.get('expires_in', 7200)
                social_account.token_expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
                social_account.save()
                logger.info(f"Successfully refreshed Twitter token for {social_account.user}")
                return True
            else:
                logger.error(f"Twitter token refresh failed: {response.text}")
                return False
        except Exception as e:
            logger.exception(f"Exception refreshing Twitter token: {e}")
            return False

    @staticmethod
    def post_to_twitter(social_account, text, media_file=None, retry=True):
        """
        Post text to Twitter (X) using V2 API.
        Auto-refreshes token on 401.
        """
        access_token = social_account.access_token
        media_id = None
        
        # 1. Upload Media (requires v1.1 API)
        if media_file:
            # Twitter's v1.1 media upload API requires OAuth 1.0a authentication.
            # Current implementation uses OAuth 2.0 PKCE which doesn't support media upload.
            logger.warning("Twitter media upload skipped: OAuth 1.0a required for media upload. Posting text only.")

        url = "https://api.twitter.com/2/tweets"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "text": text
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            data = response.json()
            post_id = data['data']['id']
            return {
                'success': True,
                'id': post_id,
                'url': f"https://twitter.com/user/status/{post_id}" 
            }
        elif response.status_code == 401 and retry:
            logger.info("Twitter 401 Unauthorized. Attempting token refresh...")
            if SocialMediaService.refresh_twitter_token(social_account):
                # Retry recursively once
                return SocialMediaService.post_to_twitter(social_account, text, media_file, retry=False)
            else:
                 return {
                    'success': False,
                    'error': "Authentication failed. Re-connect your Twitter account."
                }
        elif response.status_code == 403 or response.status_code == 429:
            # Handle Usage Limits
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
            
            # Check for usage cap error specifically
            # Twitter V2 errors are usually in 'errors' list or 'detail'
            detail = error_data.get('detail', '')
            title = error_data.get('title', '')
            
            # Common limitation messages
            if "UsageCapExceeded" in str(error_data) or "UsageCapExceeded" in str(detail):
                 return {
                    'success': False,
                    'error': "Twitter App Monthly Limit Reached. The platform's Free Tier limit (1500 posts/mo) has been exhausted for all users. Please try again next month."
                }
            
            return {
                'success': False,
                'error': f"Twitter Permission/Limit Error: {title} - {detail}"
            }
        else:
            return {
                'success': False,
                'error': response.text
            }

    @staticmethod
    def post_to_youtube(access_token, title, description, video_file, privacy_status='private'):
        """
        Post video to YouTube using Data API v3.
        """
        # Upload URL (using simple upload for simplicity, resumable is robust but complex)
        # For larger files, resumable is recommended. Here we implement the multipart upload.
        url = "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status"
        
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        metadata = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["repurposed", "uploadanywhere"],
                "categoryId": "22" # People & Blogs
            },
            "status": {
                "privacyStatus": privacy_status
            }
        }
        
        files = {
            'snippet': ('snippet.json', json.dumps(metadata), 'application/json'),
            'body': ('video.mp4', video_file, 'application/octet-stream')
        }
        
        # Reset file pointer
        if hasattr(video_file, 'seek'):
            video_file.seek(0)
            
        response = requests.post(url, headers=headers, files=files)
        
        if response.status_code in [200, 201]:
            data = response.json()
            return {
                'success': True,
                'id': data.get('id'),
                'url': f"https://www.youtube.com/watch?v={data.get('id')}"
            }
        else:
            logger.error(f"YouTube upload failed: {response.text}")
            error_msg = response.text
            try:
                err_data = response.json()
                if 'error' in err_data:
                    errors = err_data['error'].get('errors', [])
                    for e in errors:
                        if e.get('reason') == 'youtubeSignupRequired':
                            return {
                                'success': False,
                                'error': "No YouTube channel linked to this account. Please create a channel on YouTube first."
                            }
                    error_msg = err_data['error'].get('message', error_msg)
            except:
                pass
                
            return {
                'success': False,
                'error': f"YouTube Error: {error_msg}"
            }

    @staticmethod
    def post_to_instagram(access_token, ig_user_id, caption, image_url):
        """
        Post image to Instagram Feed.
        Requires 2 steps: Create Container -> Publish Container.
        Note: image_url must be on a public server accessible by Facebook servers.
        """
        # 1. Create Media Container
        container_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
        
        payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token
        }
        
        res = requests.post(container_url, data=payload)
        
        # Check container creation
        if res.status_code != 200:
            logger.error(f"Instagram container failed: {res.text}")
            return {'success': False, 'error': f"Container creation failed: {res.text}"}
            
        creation_id = res.json().get('id')
        
        # 2. Publish Container
        publish_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        
        pub_res = requests.post(publish_url, data=publish_payload)
        
        if pub_res.status_code == 200:
            data = pub_res.json()
            return {
                'success': True,
                'id': data.get('id'),
                'url': f"https://www.instagram.com/p/{data.get('id')}/" # Note: API doesn't return full URL usually, just ID
            }
        else:
            logger.error(f"Instagram publish failed: {pub_res.text}")
            return {
                'success': False,
                'error': f"Publishing failed: {pub_res.text}"
            }

    @staticmethod
    def post_to_facebook(page_access_token, page_id, message, image_url=None):
        """
        Post to Facebook Page feed.
        Uses Page Access Token (not User Token).
        """
        url = f"https://graph.facebook.com/v21.0/{page_id}/feed"
        
        payload = {
            'message': message,
            'access_token': page_access_token
        }
        
        # If image URL provided, post as photo instead
        if image_url:
            url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
            payload['url'] = image_url
        
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            data = response.json()
            post_id = data.get('id') or data.get('post_id')
            return {
                'success': True,
                'id': post_id,
                'url': f"https://www.facebook.com/{post_id}"
            }
        else:
            logger.error(f"Facebook posting failed: {response.text}")
            return {
                'success': False,
                'error': response.text
            }
