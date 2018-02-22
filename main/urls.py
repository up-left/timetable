from django.conf.urls import url
from django.urls import path
from django.contrib import admin

from . import views, admin as app_admin


urlpatterns = [
    path('table/<int:pk>/', views.TableDetailView.as_view(), name='table-details'),
    path('table/<int:pk>/image.png', views.table_image, name='table-image'),
    path('table/autocreate', app_admin.autocreate_table, name='table-autocreate'),
]

admin.site.site_title = 'Расписания'
admin.site.site_header = 'Расписания'
admin.site.index_title = ''
