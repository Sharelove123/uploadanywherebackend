from django.urls import path
from .views import (
    TeamListView, InviteMemberView, PendingInvitationsListView, 
    CancelInvitationView, AcceptInvitationView, ValidateInvitationView
)

urlpatterns = [
    path('', TeamListView.as_view(), name='team-list'),
    path('invite/', InviteMemberView.as_view(), name='invite-member'),
    path('invitations/', PendingInvitationsListView.as_view(), name='pending-invitations'),
    path('invitations/<int:pk>/cancel/', CancelInvitationView.as_view(), name='cancel-invitation'),
    path('accept-invite/', AcceptInvitationView.as_view(), name='accept-invite'),
    path('validate-invite/<str:token>/', ValidateInvitationView.as_view(), name='validate-invite'),
]
