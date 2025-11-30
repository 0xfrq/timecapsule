from django.urls import path
from .views import RegisterView, LoginView, LogoutView, ProfileView, PublicProfileView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("profiles/<str:username>/", PublicProfileView.as_view()),
]
