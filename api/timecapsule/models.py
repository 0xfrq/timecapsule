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

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('video', 'Video'),
        ('photo', 'Photo'),
        ('none', 'None'),
    ]
    
    url = models.TextField()
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    thumb_url = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)

    def __str__(self):
        return f"Post {self.id} ({self.media_type})"

class PostTime(models.Model):
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name='timestamp')
    year = models.IntegerField()

    def __str__(self):
        return f"Year {self.year} for Post {self.post.id}"

class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        # Prevent double likes
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} likes Post {self.post.id}"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    
    # ‘dummy_user_id’ for clarity that this is not a real user
    dummy_user_id = models.IntegerField(null=True, blank=True)
    
    # Self-reference for Reply feature
    parent_comment = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    text = models.TextField()

    def __str__(self):
        return f"Comment {self.id} on Post {self.post.id}"