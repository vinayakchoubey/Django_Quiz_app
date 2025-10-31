from django.urls import path
from . import views




urlpatterns = [
    path('register/', views.register, name='register'),
     path('profile/', views.profile, name='profile'),
    path('user/<str:username>/', views.user_public_profile, name='public_profile'),
]