from django.urls import path

from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/payment/', views.payment, name='payment'),
    path('orders/<str:order_number>/paypal/create/', views.paypal_create, name='paypal_create'),
    path('orders/<str:order_number>/paypal/capture/', views.paypal_capture, name='paypal_capture'),
    path('orders/<str:order_number>/cancel/', views.order_cancel, name='order_cancel'),
    path('orders/<str:order_number>/complete/', views.order_complete, name='order_complete'),
]
