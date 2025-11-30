from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.validators import UniqueValidator
from timecapsule.models import Profile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "user",
            "profile_picture",
            "bio",
            "created_at",
            "updated_at",
        )


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, validators=[UniqueValidator(queryset=User.objects.all())])
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)

    def create(self, validated_data):
        username = validated_data.get("username")
        email = validated_data.get("email", "")
        password = validated_data.get("password")
        user = User.objects.create_user(username=username, email=email, password=password)
        Profile.objects.get_or_create(user=user)
        return user
