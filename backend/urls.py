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

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # ── JWT Authentication endpoints ──────────────────────────────────────
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── Public read endpoints ─────────────────────────────────────────────
    path('api/reactions/', views.get_reactions, name='get_reactions'),
    path('api/interactions/', views.get_interactions, name='get_interactions'),

    # ── Authenticated write endpoints (Postgres legacy) ───────────────────
    path('api/add-reaction/', views.add_reaction, name='add_reaction'),
    path('api/add-interaction/', views.add_interaction, name='add_interaction'),

    # ── JSON Engine Management APIs (Admin Dashboard) ──────────────────────
    path('api/engine/rules/', views.get_engine_rules, name='get_engine_rules'),
    path('api/engine/rules/add/', views.add_engine_rule, name='add_engine_rule'),
    path('api/engine/rules/delete/', views.delete_engine_rule, name='delete_engine_rule'),

    # ── Public timeline analysis engine ───────────────────────────────────
    path('api/check-timeline/', views.check_timeline, name='check_timeline'),

    # ── Frontend HTML serving ─────────────────────────────────────────────
    # Root URL serves the patient portal
    path('', serve, {'document_root': FRONTEND_DIR, 'path': 'index.html'}, name='home'),
    # Serve any file from the frontend directory (login, dashboard, etc.)
    re_path(r'^(?P<path>(?:index\.html|admin_login\.html|admin_dashboard\.html))$',
            serve, {'document_root': FRONTEND_DIR}),
]