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
    
    path('search-drugs/', views.search_drugs, name='search_drugs'),
    path('all-drugs/', views.get_all_drugs, name='get_all_drugs'),
    path('check-timeline/', views.check_timeline, name='check_timeline'),
    path('debug-db/', views.debug_db, name='debug-db'),
    path('seed-test-pair/', views.seed_test_pair, name='seed_test_pair'),
    path('seed-massive/', views.trigger_massive_seed, name='seed_massive'),

    # Drug Dictionary Management
    path('admin/drugs/', views.list_drugs, name='list_drugs'),
    path('admin/drugs/create/', views.create_drug, name='create_drug'),
    path('admin/drugs/delete/', views.delete_drug, name='delete_drug'),
]
