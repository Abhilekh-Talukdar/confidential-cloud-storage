# storage/urls.py
from django.urls import path
from . import views

app_name = 'storage'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('upload/', views.upload_page_view, name='upload_page'),
    path('download/', views.download_list_view, name='download_list'),
    path('download/file/', views.download_file_view, name='download_file'),
    # Add this line for the delete action
    path('delete/<int:file_id>/', views.delete_file_view, name='delete_file'),
]