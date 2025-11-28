from django.db import models
from django.contrib.auth.models import User

def profile_picture_upload_path(instance, filename):
    return f"profile_pictures/user_{instance.user.id}/{filename}"

def banner_upload_path(instance, filename):
    return f"banners/user_{instance.user.id}/{filename}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_path,
        blank=True,
        null=True,
    )

    bio = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.username}"


class Banner(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="banners")

    # Image
    image = models.ImageField(
        upload_to=banner_upload_path,
        blank=True,
        null=True,
    )

    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Banner for {self.profile.user.username} - {self.title or 'Untitled'}"
