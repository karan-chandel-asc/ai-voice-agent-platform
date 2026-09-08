from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    """Serialize public CustomUser profile fields.

    Exposes id, email, business, and phone.
    id and created_at are read-only.
    """

    class Meta:
        model = CustomUser
        fields = ["id", "email", "username", "business_name", "phone", "created_at"]
        read_only_fields = ["id", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    """Create a CustomUser with a hashed password.

    Accepts email, username, password, and profile fields.
    Password is write-only with a minimum length of 8.
    """

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ["email", "username", "password", "business_name", "phone"]

    def create(self, validated_data):
        """Create the user via create_user for hashing."""
        return CustomUser.objects.create_user(**validated_data)


class CustomTokenSerializer(TokenObtainPairSerializer):
    """Issue JWT pair and attach serialized user data.

    Extends SimpleJWT TokenObtainPairSerializer.
    Adds a nested user object to the token response.
    """

    def validate(self, attrs):
        """Return tokens plus UserSerializer payload."""
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
