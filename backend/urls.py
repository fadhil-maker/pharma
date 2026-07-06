from django.contrib import admin
from django.urls import path
from tracker import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/drugs/', views.get_drugs, name='get_drugs'),
    path('api/reactions/', views.get_reactions, name='get_reactions'),
    path('api/add-reaction/', views.add_reaction, name='add_reaction'),
    path('api/add-interaction/', views.add_interaction, name='add_interaction'),
    path('api/check-timeline/', views.check_timeline, name='check_timeline'),
]