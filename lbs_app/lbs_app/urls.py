from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('library_app.urls')),  # Replace 'library_app' with your app's name
]
