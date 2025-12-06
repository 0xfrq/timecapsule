from django.contrib import admin
from .models import Profile, Banner, Post, Tag, PostTime, Comment, PostLike

admin.site.register(Profile)
admin.site.register(Banner)
admin.site.register(Post)
admin.site.register(Tag)
admin.site.register(PostTime)
admin.site.register(Comment)
admin.site.register(PostLike)