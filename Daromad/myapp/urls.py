# myapp/urls.py (yoki finances/urls.py)
from django.urls import path
from myapp.views import *

urlpatterns = [
    path('login/', user_login, name='login'),
    path('register/', user_register, name='register'),
    path('logout/', user_logout, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/update/', update_profile, name='profile_update'),

    path('', dashboard_view, name='dashboard'), 
    path('<int:year>/<int:month>/', dashboard_view, name='dashboard_select_month'),
    path('transactions/list-partial/', get_transactions_list_partial, name='transactions_list_partial'), 
   

    path('profile/about/', about_view, name='about'),

    # Tranzaksiya
    path('transaction/add/', add_transaction_view, name='add_transaction'),
    path('category/add/', add_category_view, name='add_category'),
    path('category/delete/<int:category_id>/', delete_category_view, name='category_delete'),
    
    # Takrorlanuvchi Jadval (Wallet tugmasi)
    path('recurring/', recurring_list_view, name='recurring_list'),
    path('recurring/add/', add_recurring_view, name='add_recurring'),
    path('recurring/delete/<int:pk>/', delete_recurring_view, name='delete_recurring'),
     
    # Budjet
    path('profile/budget_about/', budget_about, name='budget_about'),
]