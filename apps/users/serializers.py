"""
Serializers for User model.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'password_confirm', 'first_name', 'last_name']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': "Passwords don't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""
    pk = serializers.IntegerField(source='id', read_only=True)
    repurposes_remaining = serializers.SerializerMethodField()
    subscription_tier = serializers.SerializerMethodField()
    subscription_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'pk', 'id', 'email', 'username', 'first_name', 'last_name',
            'avatar', 'bio', 'subscription_tier', 'subscription_display',
            'repurposes_used_this_month', 'repurposes_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'pk', 'id', 'email', 'subscription_tier', 'repurposes_used_this_month',
            'created_at', 'updated_at'
        ]

    def get_subscription_tier(self, obj) -> str:
        """Get subscription tier from user."""
        return obj.subscription_tier or 'free'

    def get_subscription_display(self, obj) -> str:
        """Get display name for subscription tier."""
        tier = self.get_subscription_tier(obj)
        return tier.capitalize()

    def get_repurposes_remaining(self, obj) -> int:
        from django.conf import settings
        tier = self.get_subscription_tier(obj)
        limits = settings.SUBSCRIPTION_LIMITS.get(tier, {})
        max_repurposes = limits.get('repurposes_per_month', 0)
        
        if max_repurposes == -1:
            return -1  # Unlimited
        return max(0, max_repurposes - obj.repurposes_used_this_month)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
