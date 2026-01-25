from rest_framework import generics, permissions
from .permissions import IsTeamAdminOrOwner, IsInviterOrAdminOrOwner
from .models import TeamMembership, TeamInvitation
from .serializers import TeamMembershipSerializer, TeamInvitationSerializer

class TeamListView(generics.ListCreateAPIView):
    queryset = TeamMembership.objects.all()
    serializer_class = TeamMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter by current user
        return self.queryset.filter(user=self.request.user)


class InviteMemberView(generics.CreateAPIView):
    serializer_class = TeamInvitationSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamAdminOrOwner]

    def perform_create(self, serializer):
        from django.utils import timezone
        import uuid
        
        # Check if user already exists
        # In a real app, you might want to handle this differently (e.g. add existing user to team)
        # For now, we assume completely new users for invites
        
        token = str(uuid.uuid4())
        # Expires in 7 days
        expires_at = timezone.now() + timezone.timedelta(days=7)
        
        serializer.save(
            invited_by=self.request.user,
            token=token,
            expires_at=expires_at
        )

        # Send invitation email
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Build invite link
        # Use request origin to handle subdomains correctly
        origin = self.request.META.get('HTTP_ORIGIN', settings.FRONTEND_URL)
        invite_link = f"{origin}/signup?token={token}"
        
        subject = f"You've been invited to join {self.request.tenant.name}"
        message = f"""
        Hello!
        
        You have been invited to join the team at {self.request.tenant.name}.
        
        Click the link below to accept the invitation and set up your account:
        {invite_link}
        
        This link will expire in 7 days.
        
        Best regards,
        The {self.request.tenant.name} Team
        """
        
        try:
             send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [serializer.validated_data['email']],
                fail_silently=False,
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send email: {e}")


class PendingInvitationsListView(generics.ListAPIView):
    queryset = TeamInvitation.objects.all()
    serializer_class = TeamInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Show all pending invites for this tenant
        # Since schemas isolate data, we just need to filter by unaccepted/unexpired
        # But for now, let's just return all invites made by the team
        return TeamInvitation.objects.filter(accepted=False).order_by('-created_at')


class CancelInvitationView(generics.DestroyAPIView):
    queryset = TeamInvitation.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsInviterOrAdminOrOwner]


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class AcceptInvitationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        password = request.data.get('password')
        
        if not token or not password:
            return Response({'error': 'Token and password are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            invite = TeamInvitation.objects.get(token=token, accepted=False)
        except TeamInvitation.DoesNotExist:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_404_NOT_FOUND)
            
        from django.utils import timezone
        if invite.expires_at < timezone.now():
             return Response({'error': 'Invitation expired'}, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=invite.email,  # Use email as username
                    email=invite.email,
                    password=password,
                    is_active=True
                )
                
                # Add to team
                TeamMembership.objects.create(
                    user=user,
                    role=invite.role,
                    invited_by=invite.invited_by,
                    accepted_at=timezone.now()
                )
                
                # Mark invite accepted
                invite.accepted = True
                invite.save()
                
                # Update UserTenantMap in PUBLIC schema
                # We need to switch to public schema to write to UserTenantMap
                from django_tenants.utils import schema_context
                from apps.tenants.models import UserTenantMap
                from django.db import connection
                
                # Get current tenant (Client)
                current_tenant = connection.tenant
                
                with schema_context('public'):
                    UserTenantMap.objects.get_or_create(
                        email=user.email,
                        defaults={'tenant': current_tenant} 
                    )
                    # Note: If user belongs to multiple tenants, this simple map 
                    # might only store the first one or need a ManyToMany approach.
                    # For now, we assume 1:1 or we just redirect to the first one found.
                    # If we used get_or_create, it won't overwrite existing map associated with another tenant if email unique.
                    # Ideally UserTenantMap should allow multiple? 
                    # But for redirection we probably want a "default" or just check if they exist.
                    # Let's stick to 1:1 for simplicity or update if needed. 
                    # Actually valid requirement: User could belong to multiple teams with same email?
                    # If so, UserTenantMap email should NOT be unique in model logic if we want to support multiple.
                    # But the model I created has unique=True.
                    # For this implementation, I will assume unique=True (1 user -> 1 tenant main mapping).
                    # If they join another, we might update it or fail.
                    # Let's use update_or_create to point to latest tenant?
                    
                    UserTenantMap.objects.update_or_create(
                        email=user.email,
                        defaults={'tenant': current_tenant}
                    )
                
                return Response({'message': 'Invitation accepted. Please login.'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ValidateInvitationView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, token):
        try:
            invite = TeamInvitation.objects.get(token=token, accepted=False)
            from django.utils import timezone
            if invite.expires_at < timezone.now():
                return Response({'valid': False, 'error': 'Expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'valid': True, 
                'email': invite.email,
                'role': invite.role
            })
        except TeamInvitation.DoesNotExist:
             return Response({'valid': False, 'error': 'Invalid'}, status=status.HTTP_404_NOT_FOUND)
