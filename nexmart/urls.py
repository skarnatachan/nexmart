from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.http import HttpResponse

urlpatterns = [
    path('health/', lambda request: HttpResponse('ok'), name='health'),  # load balancer health check
    # Fake admin: logs every attempt in the (real) admin under "Login attempts".
    path("admin/", include("admin_honeypot.urls", namespace="admin_honeypot")),
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    path('', include('store.urls')),
    path('account/', include('account.urls')),
    path('cart/', include('carts.urls')),
    path('', include('orders.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)