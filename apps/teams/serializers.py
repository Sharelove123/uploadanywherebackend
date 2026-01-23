from rest_framework import serializers
from .models import TeamMembership, TeamInvitation

class TeamMembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = TeamMembership
        fields = '__all__'
        read_only_fields = ['invited_by', 'invited_at', 'accepted_at']

class TeamInvitationSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = TeamInvitation
        fields = ['id', 'email', 'role', 'invited_by', 'invited_by_email', 'created_at', 'expires_at', 'accepted', 'status']
        read_only_fields = ['invited_by', 'token', 'created_at', 'expires_at', 'accepted']

    def get_status(self, obj):
        from django.utils import timezone
        if obj.accepted:
            return 'accepted'
        if obj.expires_at < timezone.now():
            return 'expired'
        return 'pending'
