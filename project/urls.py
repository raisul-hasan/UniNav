from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from login import views

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # Main app (login, register, map, etc.)
    path('', include('login.urls')),

    
]

# ------------------------------------------------------------------
# 🔹 Serve static & media files during development
# ------------------------------------------------------------------

# Serve STATIC files (CSS, JS, images)
urlpatterns += static(
    settings.STATIC_URL,
    document_root=settings.STATICFILES_DIRS[0] if getattr(settings, "STATICFILES_DIRS", None) else settings.STATIC_ROOT
)

# Serve MEDIA files (uploads)
urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)


