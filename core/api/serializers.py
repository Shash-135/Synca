from rest_framework import serializers

from ..models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer exposing the current user's public profile information."""

    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'user_type',
            'contact_number',
            'profile_photo',
        )
        read_only_fields = fields

    def get_profile_photo(self, obj):
        if not obj.profile_photo:
            return None
        request = self.context.get('request')
        photo_url = obj.profile_photo.url
        if request is None:
            return photo_url
        return request.build_absolute_uri(photo_url)
