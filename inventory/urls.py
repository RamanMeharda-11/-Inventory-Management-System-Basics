from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),

    path('add/', views.add_product, name='add_product'),
    path('products/', views.view_products, name='view_products'),
    path('products/<str:pk>/update/', views.update_product, name='update_product'),
    path('products/<str:pk>/delete/', views.delete_product, name='delete_product'),
    path('search/', views.search_product, name='search_product'),

    path('sell/', views.sell_product, name='sell_product'),

    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
    path('reports/summary/', views.inventory_summary, name='inventory_summary'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/sales/export/', views.export_sales_csv, name='export_sales_csv'),

    path('account/change-password/', views.change_password, name='change_password'),
]