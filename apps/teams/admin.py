from django.contrib import admin
from .models import TeamMembership, TeamInvitation

@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_active', 'invited_by')
    search_fields = ('user__email', 'user__username')
    list_filter = ('role', 'is_active')

@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'invited_by', 'created_at', 'accepted')
    search_fields = ('email',)
    list_filter = ('role', 'accepted')
