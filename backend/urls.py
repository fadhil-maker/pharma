from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.conf import settings
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from tracker import views

# Resolve the frontend directory relative to BASE_DIR
FRONTEND_DIR = settings.BASE_DIR / 'frontend'

from django.views.decorators.cache import never_cache

@never_cache
def serve_no_cache(request, path, document_root=None):
    response = serve(request, path, document_root=document_root)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # ── JWT Authentication endpoints ──────────────────────────────────────
    path('api/setup-admin/', views.setup_admin, name='setup_admin'),
    path('api/admin/me/', views.admin_profile, name='admin_profile'),
    path('api/admin/list/', views.list_admins, name='list_admins'),
    path('api/admin/add/', views.add_admin, name='add_admin'),
    path('api/admin/delete/', views.delete_admin, name='delete_admin'),
    path('api/admin/reset-password/', views.reset_admin_password, name='reset_admin_password'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── Public read endpoints ─────────────────────────────────────────────
    path('api/reactions/', views.get_reactions, name='get_reactions'),
    path('api/interactions/', views.get_interactions, name='get_interactions'),

    # ── Authenticated write endpoints (Postgres legacy) ───────────────────
    path('api/add-reaction/', views.add_reaction, name='add_reaction'),
    path('api/add-interaction/', views.add_interaction, name='add_interaction'),

    # ── Smart SQL Engine Management APIs (Admin Dashboard) ─────────────────
    path('api/engine/rules/', views.get_engine_rules, name='get_engine_rules'),
    path('api/engine/rules/add/', views.smart_check_and_add_rule, name='smart_check_and_add_rule'),
    path('api/engine/rules/delete/', views.delete_engine_rule, name='delete_engine_rule'),
    path('api/engine/seed/', views.seed_database_api, name='seed_database_api'),

    # ── Public timeline analysis engine ───────────────────────────────────
    path('api/check-timeline/', views.check_timeline, name='check_timeline'),

    # ── Frontend HTML serving (FORCE HTTP NO-CACHE RESPONSE HEADERS) ──────
    path('', serve_no_cache, {'document_root': FRONTEND_DIR, 'path': 'index.html'}, name='home'),
    path('fadhil', serve_no_cache, {'document_root': FRONTEND_DIR, 'path': 'fadhil.html'}, name='fadhil_admin'),
    re_path(r'^(?P<path>(?:index\.html|admin_login\.html|admin_dashboard\.html|fadhil|fadhil\.html|all_drugs\.js))$',
            serve_no_cache, {'document_root': FRONTEND_DIR}),
]