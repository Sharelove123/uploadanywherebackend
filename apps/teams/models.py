from django.db import models
from django.conf import settings


class TeamMembership(models.Model):
    """
    Links users to roles within a tenant.
    Only applicable for company-type tenants.
    """
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'          # Full access + billing
        ADMIN = 'admin', 'Admin'          # Full access, no billing
        MEMBER = 'member', 'Member'       # Can create content
        VIEWER = 'viewer', 'Viewer'       # Read-only access
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invitations_sent'
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        # User can only have one membership per tenant (enforced by schema isolation)
        pass

    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"


class TeamInvitation(models.Model):
    """Pending invitations for team members."""
    
    email = models.EmailField()
    role = models.CharField(
        max_length=20, 
        choices=TeamMembership.Role.choices,
        default=TeamMembership.Role.MEMBER
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    token = models.CharField(max_length=255, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Invite: {self.email} as {self.get_role_display()}"
