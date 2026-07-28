from django.urls import path
from . import views

urlpatterns = [
    path('setup-admin/', views.setup_admin, name='setup_admin'),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/list/', views.list_admins, name='list_admins'),
    path('admin/add/', views.add_admin, name='add_admin'),
    
    path('admin/interactions/', views.list_interactions, name='list_interactions'),
    path('admin/interactions/create/', views.create_interaction, name='create_interaction'),
    path('admin/interactions/delete/', views.delete_interaction, name='delete_interaction'),
    path('admin/interactions/smart-fetch/', views.smart_fetch_drug_interactions, name='smart_fetch_drug_interactions'),
    
        path('search-drugs/', views.search_drugs, name='search_drugs'),
    path('check-timeline/', views.check_timeline, name='check_timeline'),
]
