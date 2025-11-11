from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView

from .serializers import UserSerializer

class CurrentUserView(RetrieveAPIView):
    """Return the authenticated user's profile information."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
