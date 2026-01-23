from django.urls import path, include

urlpatterns = [
    # Auth - Login only (no public registration on tenant subdomains)
    path('api/auth/', include('dj_rest_auth.urls')),
    # Registration disabled for security - admins add team members via dashboard
    # path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # App logic
    path('api/users/', include('apps.users.urls')),
    path('api/teams/', include('apps.teams.urls')),
    path('api/repurposer/', include('apps.repurposer.urls')),
    path('api/social/', include('apps.social_accounts.urls')),
    path('api/payments/', include('apps.payments.urls')),
]

