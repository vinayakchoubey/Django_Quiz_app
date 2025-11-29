from django.contrib import admin
from django.urls import include, path
from users import views as user_views

urlpatterns = [
    # Django admin (staff-only, uses its own login)
    path('admin/', admin.site.urls),

    # Public quiz site
    path('', include('quizzes.urls')),

    # Auth for regular users (quiz participants)
    path('login/', user_views.UserLoginView.as_view(), name='login'),
    path('logout/', user_views.logout_view, name='logout'),
    path('register/', user_views.register, name='register'),

    # Separate admin login & in-app dashboard (staff-only)
    path('admin-login/', user_views.AdminLoginView.as_view(), name='admin_login'),
    path('admin-dashboard/', user_views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/reattempt/<int:pk>/', user_views.handle_reattempt_request, name='handle_reattempt_request'),
]