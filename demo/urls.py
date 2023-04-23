from django.contrib import admin
from django.urls import path

from .views import index

admin.autodiscover()

urlpatterns = [
    # path("", debug.default_urlconf),
    path("", index, name="index"),
    path("admin/", admin.site.urls),
]
