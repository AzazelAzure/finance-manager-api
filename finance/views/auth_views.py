from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
import os

# Base callback URL for local development/simulation
# In production, this would be the actual frontend URL
CALLBACK_URL = os.getenv("OAUTH_CALLBACK_URL", "https://financemanager.local:8443/auth/callback/")

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = CALLBACK_URL
    client_class = OAuth2Client

class GitHubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    callback_url = CALLBACK_URL
    client_class = OAuth2Client
