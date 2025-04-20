# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings           # Import settings
from django.conf.urls.static import static # Import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('storage.urls')), # Include your app's URLs
]

# Add this for serving media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)