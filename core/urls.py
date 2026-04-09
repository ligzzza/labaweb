from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from main.views import home, UserListView

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('main.urls')),
    path('api/users/', UserListView.as_view(), name='user-list'),
    path('api-auth/', include('rest_framework.urls')),
]

# Для работы с медиафайлами (изображения) в режиме разработки
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)