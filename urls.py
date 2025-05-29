# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),  # This makes login.html load on port 8000

    path('login/', views.login_view, name='login'),
    # path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home_view, name='home'),
    # path('profile/', views.profile_view, name='profile'),  # optional
    # path('change-password/', views.change_password_view, name='change_password'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('members/', views.members_view, name = "members"),
    path('analytics/', views.analytics_view, name = 'analytics')
]