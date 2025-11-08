from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import UserSerializer


class UserTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that injects user metadata into the token payload."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_type'] = getattr(user, 'user_type', None)
        token['username'] = user.get_username()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user, context=self.context).data
        return data


class UserTokenObtainPairView(TokenObtainPairView):
    """Return a JWT pair along with serialized user information."""

    serializer_class = UserTokenObtainPairSerializer


class UserTokenRefreshView(TokenRefreshView):
    """Expose the refresh endpoint for convenience."""

    pass


class CurrentUserView(RetrieveAPIView):
    """Return the authenticated user's profile information."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
