
import logging
import requests
from django.conf import settings
from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import SocialAccount
from .serializers import SocialAccountSerializer

logger = logging.getLogger(__name__)

class SocialConnectView(views.APIView):
    """
    Returns the authorization URL for the specified platform.
    Frontend should redirect the user to this URL.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, platform):
        # Get the origin domain from the request to build dynamic redirect_uri
        origin = request.META.get('HTTP_ORIGIN', '')
        tenant_domain = request.META.get('HTTP_X_TENANT_DOMAIN', '')
        
        # Determine the frontend base URL
        if origin:
            frontend_base = origin
        elif tenant_domain:
            # Build from tenant domain header
            frontend_base = f"http://{tenant_domain}"
            if ':' not in tenant_domain:
                frontend_base = f"http://{tenant_domain}:3000"
        else:
            frontend_base = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'
        
        if platform == 'linkedin':
            config = self._get_linkedin_config(frontend_base)
        elif platform == 'twitter':
            config = self._get_twitter_config(frontend_base, request)
        elif platform == 'youtube':
            config = self._get_youtube_config(frontend_base)
        elif platform == 'instagram':
            config = self._get_instagram_config(frontend_base)
        else:
            return Response({'error': 'Unsupported platform'}, status=status.HTTP_400_BAD_REQUEST)

        if not config.get('client_id'):
            return Response(
                {'error': f'Server configuration missing: {platform.upper()} Client ID not set.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        auth_url = (
            f"{config['auth_endpoint']}?"
            f"response_type=code&"
            f"client_id={config['client_id']}&"
            f"redirect_uri={config['redirect_uri']}&"
            f"state={request.user.id}&"
            f"scope={config['scope']}"
        )
        
        if 'code_challenge' in config:
            auth_url += f"&code_challenge={config['code_challenge']}&code_challenge_method={config['code_challenge_method']}"
            
        if 'access_type' in config:
            auth_url += f"&access_type={config['access_type']}&prompt={config['prompt']}"
        
        # Store the redirect_uri in session so callback can use the same one
        request.session['oauth_redirect_uri'] = config['redirect_uri']
        request.session['oauth_platform'] = platform

        return Response({'url': auth_url})

    def _get_linkedin_config(self, frontend_base):
        return {
            'auth_endpoint': 'https://www.linkedin.com/oauth/v2/authorization',
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'redirect_uri': f"{frontend_base}/callback/linkedin",
            'scope': 'w_member_social openid profile email', 
        }

    def _get_twitter_config(self, frontend_base, request=None):
        import secrets
        import hashlib
        import base64

        # Generate PKCE verifier and challenge
        code_verifier = secrets.token_urlsafe(64)
        hashed = hashlib.sha256(code_verifier.encode('ascii')).digest()
        code_challenge = base64.urlsafe_b64encode(hashed).decode('ascii').rstrip('=')
        
        # Store verifier in session if request provided
        if request:
            request.session['oauth_verifier'] = code_verifier

        return {
            'auth_endpoint': 'https://twitter.com/i/oauth2/authorize',
            'client_id': getattr(settings, 'TWITTER_CLIENT_ID', settings.TWITTER_API_KEY),
            'redirect_uri': f"{frontend_base}/callback/twitter",
            'scope': 'tweet.read tweet.write users.read offline.access',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }

    def _get_youtube_config(self, frontend_base):
        return {
            'auth_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth',
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'scope': 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/userinfo.profile',
            'access_type': 'offline',
            'prompt': 'consent'
        }

    def _get_instagram_config(self, frontend_base):
        return {
            'auth_endpoint': 'https://www.facebook.com/v18.0/dialog/oauth',
            'client_id': settings.FACEBOOK_APP_ID,
            'redirect_uri': f"{frontend_base}/callback/instagram",
            'scope': 'instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement',
        }


class SocialCallbackView(views.APIView):
    """
    Handles the callback from the social platform.
    Exchanges code for access token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, platform):
        code = request.data.get('code')
        if not code:
            return Response({'error': 'No code provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the redirect_uri that was used during connect (must match exactly)
        origin = request.META.get('HTTP_ORIGIN', '')
        tenant_domain = request.META.get('HTTP_X_TENANT_DOMAIN', '')
        
        if origin:
            frontend_base = origin
        elif tenant_domain:
            frontend_base = f"http://{tenant_domain}"
            if ':' not in tenant_domain:
                frontend_base = f"http://{tenant_domain}:3000"
        else:
            frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        
        if platform == 'youtube':
            redirect_uri = settings.GOOGLE_REDIRECT_URI
        else:
            redirect_uri = f"{frontend_base}/callback/{platform}"

        if platform == 'linkedin':
            token_data = self._exchange_linkedin_token(code, redirect_uri)
        elif platform == 'twitter':
            code_verifier = request.session.get('oauth_verifier')
            token_data = self._exchange_twitter_token(code, redirect_uri, code_verifier)
        elif platform == 'youtube':
            token_data = self._exchange_youtube_token(code, redirect_uri)
        elif platform == 'instagram':
            token_data = self._exchange_instagram_token(code, redirect_uri)
        else:
            return Response({'error': 'Unsupported platform'}, status=status.HTTP_400_BAD_REQUEST)

        if not token_data or 'error' in token_data:
            print(f"Token Error: {token_data}")  # Debug print
            return Response({'error': 'Failed to obtain token', 'details': token_data}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get profile info
        platform_user_id = 'unknown'
        platform_username = 'unknown'

        if platform == 'linkedin':
            user_info = self._get_linkedin_user_info(token_data.get('access_token'))
            if user_info:
                platform_user_id = user_info.get('sub') or user_info.get('id') or 'unknown'
                if 'given_name' in user_info:
                    platform_username = f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}"
                elif 'localizedFirstName' in user_info:
                    platform_username = f"{user_info.get('localizedFirstName', '')} {user_info.get('localizedLastName', '')}"
        elif platform == 'twitter':
            user_info = self._get_twitter_user_info(token_data.get('access_token'))
            if user_info and 'data' in user_info:
                platform_user_id = user_info['data']['id']
                platform_username = user_info['data']['username']
        elif platform == 'youtube':
            user_info = self._get_youtube_user_info(token_data.get('access_token'))
            # Get channel info instead of simple profile
            channel_info = self._get_youtube_channel_info(token_data.get('access_token'))
            if channel_info and 'items' in channel_info and len(channel_info['items']) > 0:
                channel = channel_info['items'][0]
                platform_user_id = channel['id']
                platform_username = channel['snippet']['title']
            else:
                # Fallback to userinfo
                platform_user_id = user_info.get('sub') or user_info.get('id')
                platform_username = user_info.get('name') or user_info.get('email')
        elif platform == 'instagram':
            # Complex flow: User Token -> Page Token -> IG Business ID
            # Here we might just find the first available IG Business account
            ig_info = self._get_instagram_account_info(token_data.get('access_token'))
            if ig_info and 'ig_id' in ig_info:
                platform_user_id = ig_info['ig_id']
                platform_username = ig_info['username']
                # Important: The access token needed for posting is often the PAGE token or User token
                # For IG Graph API, User Access Tokens (if long-lived) often work for 'me/accounts' but 
                # posting usually requires the token associated with the User who has role on Page.
                # Simplest MVP: Store User Token (Long-lived)
            else:
                return Response({'error': 'No Instagram Business Account linked to this Facebook account.'}, status=status.HTTP_400_BAD_REQUEST)

        # Save account
        from django.utils import timezone
        from datetime import timedelta
        
        expires_in = token_data.get('expires_in')
        token_expires_at = None
        if expires_in:
            token_expires_at = timezone.now() + timedelta(seconds=int(expires_in))
        
        SocialAccount.objects.update_or_create(
            user=request.user,
            platform=platform,
            platform_user_id=platform_user_id,
            defaults={
                'access_token': token_data.get('access_token', ''),
                'refresh_token': token_data.get('refresh_token', ''),
                'token_expires_at': token_expires_at,
                'is_active': True,
                'platform_username': platform_username
            }
        )
        
        return Response({'message': f'{platform} connected successfully'})

    def _exchange_linkedin_token(self, code, redirect_uri):
        url = 'https://www.linkedin.com/oauth/v2/accessToken'
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'client_secret': settings.LINKEDIN_CLIENT_SECRET,
        }
        response = requests.post(url, data=payload)
        return response.json()

    def _get_linkedin_user_info(self, access_token):
        url = 'https://api.linkedin.com/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            url = 'https://api.linkedin.com/v2/me'
            response = requests.get(url, headers=headers)
        return response.json()

    def _exchange_twitter_token(self, code, redirect_uri, code_verifier=None):
        url = 'https://api.twitter.com/2/oauth2/token'
        import base64
        client_id = getattr(settings, 'TWITTER_CLIENT_ID', settings.TWITTER_API_KEY)
        client_secret = getattr(settings, 'TWITTER_CLIENT_SECRET', settings.TWITTER_API_SECRET)
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'client_id': client_id,
        }
        if code_verifier:
            data['code_verifier'] = code_verifier
        response = requests.post(url, data=data, headers=headers)
        return response.json()

    def _get_twitter_user_info(self, access_token):
        url = 'https://api.twitter.com/2/users/me'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(url, headers=headers)
        return response.json()

    def _exchange_youtube_token(self, code, redirect_uri):
        url = 'https://oauth2.googleapis.com/token'
        data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        response = requests.post(url, data=data)
        return response.json()

    def _get_youtube_user_info(self, access_token):
        url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(url, headers=headers)
        return response.json()

    def _get_youtube_channel_info(self, access_token):
        url = 'https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(url, headers=headers)
        return response.json()

    def _exchange_instagram_token(self, code, redirect_uri):
        # 1. Exchange Access Token
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            'client_id': settings.FACEBOOK_APP_ID,
            'redirect_uri': redirect_uri,
            'client_secret': settings.FACEBOOK_APP_SECRET,
            'code': code
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'access_token' in data:
            # 2. Exchange for Long-Lived Token (Required for offline access effectively)
            ll_url = "https://graph.facebook.com/v18.0/oauth/access_token"
            ll_params = {
                'grant_type': 'fb_exchange_token',
                'client_id': settings.FACEBOOK_APP_ID,
                'client_secret': settings.FACEBOOK_APP_SECRET,
                'fb_exchange_token': data['access_token']
            }
            ll_res = requests.get(ll_url, params=ll_params)
            ll_data = ll_res.json()
            if 'access_token' in ll_data:
                data['access_token'] = ll_data['access_token']
                data['expires_in'] = ll_data.get('expires_in')
        
        return data

    def _get_instagram_account_info(self, access_token):
        # Find IG Business Account connected to Facebook Pages
        url = "https://graph.facebook.com/v18.0/me/accounts?fields=instagram_business_account{id,username},name"
        response = requests.get(url, params={'access_token': access_token})
        data = response.json()
        
        print(f"DEBUG: Facebook Pages Response: {data}") # Debug log

        if 'data' in data:
            for page in data['data']:
                print(f"DEBUG: Checking Page: {page.get('name')} - IG: {page.get('instagram_business_account')}")
                if 'instagram_business_account' in page:
                    return {
                        'ig_id': page['instagram_business_account']['id'],
                        'username': page['instagram_business_account']['username'],
                        'page_name': page['name']
                    }
        return None




class SocialAccountListView(views.APIView):
    """
    List all connected social accounts for the current user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        accounts = SocialAccount.objects.filter(user=request.user, is_active=True)
        serializer = SocialAccountSerializer(accounts, many=True)
        return Response(serializer.data)


class SocialDisconnectView(views.APIView):
    """
    Disconnects (deactivates) a social account.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, platform):
        try:
            account = SocialAccount.objects.get(user=request.user, platform=platform, is_active=True)
            account.is_active = False
            account.save()
            return Response({'message': f'{platform} disconnected successfully'})
        except SocialAccount.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
