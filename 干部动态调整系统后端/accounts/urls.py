from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # 认证相关
    path('auth/login/', views.login_view, name='login'),
    path('auth/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/me/', views.UserProfileView.as_view(), name='user_profile'),
    path('auth/change-password/', views.change_password_view, name='change_password'),
]