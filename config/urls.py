from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('formularios/', include('formularios.urls')),
    path('', include('crm.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "MyVisaCrm.com"
admin.site.site_title = "MyVisaCrm.com Admin"
admin.site.index_title = "Welcome to MyVisaCrm.com"
