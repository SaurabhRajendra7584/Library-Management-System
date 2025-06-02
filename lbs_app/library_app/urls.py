# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),  # This will make / show home.html
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('members/', views.members_view, name='members'),
    path('analytics/', views.analytics_view, name='analytics'),
]
