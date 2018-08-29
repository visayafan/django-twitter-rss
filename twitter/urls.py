from django.urls import path

from . import views

urlpatterns = [
    path('', views.home),
    path('twitter/<str:uid>/', views.index, name='twitter')
]
