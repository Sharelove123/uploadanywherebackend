from rest_framework import permissions
from .models import TeamMembership

class IsTeamAdminOrOwner(permissions.BasePermission):
    """
    Allows access only to team admins and owners.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Check if user has a membership with admin or owner role
        # We assume the request is tenant-scoped via django-tenants
        try:
            membership = TeamMembership.objects.get(user=request.user)
            return membership.role in [TeamMembership.Role.ADMIN, TeamMembership.Role.OWNER]
        except TeamMembership.DoesNotExist:
            return False

class IsInviterOrAdminOrOwner(permissions.BasePermission):
    """
    Allows access to the inviter, or team admins/owners.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # obj is TeamInvitation
        if request.user == obj.invited_by:
            return True
        
        try:
            membership = TeamMembership.objects.get(user=request.user)
            return membership.role in [TeamMembership.Role.ADMIN, TeamMembership.Role.OWNER]
        except TeamMembership.DoesNotExist:
            return False
