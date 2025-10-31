from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from users import views as user_views  # ✅ ADD THIS IMPORT

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('quizzes.urls')),
    
    # ✅ FIXED: Remove the users/ include and define auth URLs directly
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', user_views.register, name='register'),  # ✅ ADD THIS LINE
    # path('users/', include('users.urls')), 
]