from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path('store/', views.store, name="store"),
    path('store/<slug:category_slug>/', views.store, name="products_by_category"),
    path('store/<slug:category_slug>/<slug:product_slug>/review/', views.review_submit, name='review_submit'),
    path('store/<slug:category_slug>/<slug:product_slug>/review/delete/', views.review_delete, name='review_delete'),
    path('store/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name="products_detail"),
]
