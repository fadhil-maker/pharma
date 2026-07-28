"""
Pharmacy Clinical Tracker – Full API Engine & Admin Console Views
================================================================
"""

import os
import json
import logging
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

from django.db.models import Q
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import ReactionDefinition, Interaction

logger = logging.getLogger(__name__)

# ── 1. Auto Superadmin Setup ────────────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def setup_admin(request):
    """Creates the initial superadmin account if not already present."""
    if User.objects.filter(username='admin').exists():
        return JsonResponse({"status": "Admin already exists! Username: admin | Password: adminpassword123"})
    
    user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword123')
    return JsonResponse({"status": "Success! Superadmin created. Username: admin | Password: adminpassword123"})


# ── 2. Admin Authentication & Management Endpoints ─────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """Authenticate admin user and return status."""
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    
    if not username or not password:
        return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
    user = authenticate(username=username, password=password)
    if user is not None and user.is_staff:
        return Response({
            'message': 'Login successful',
            'username': user.username,
            'is_superuser': user.is_superuser
        }, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Invalid admin credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_admins(request):
    """List all admin accounts."""
    admins = User.objects.filter(is_staff=True).values('id', 'username', 'email', 'is_superuser', 'date_joined')
    return Response({'admins': list(admins)})


@api_view(['POST'])
@permission_classes([AllowAny])
def add_admin(request):
    """Add a new admin account."""
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    email = request.data.get('email', '').strip()
    
    if not username or not password:
        return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'error': f'Username "{username}" already exists.'}, status=status.HTTP_409_CONFLICT)
        
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return Response({'message': f'Admin "{username}" created successfully!'}, status=status.HTTP_201_CREATED)


# ── 3. Rule CRUD Endpoints for Admin View ───────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def list_interactions(request):
    """List rules in database with server-side pagination, search, sorting & filtering."""
    search_q = request.GET.get('search', '').strip().lower()
    sort_by = request.GET.get('sort_by', 'id').strip().lower()
    order = request.GET.get('order', 'asc').strip().lower()
    min_severity = request.GET.get('min_severity', '').strip()
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))
    
    qs = Interaction.objects.select_related('reaction').all()
    
    if search_q:
        qs = qs.filter(
            Q(drug_a__icontains=search_q) | 
            Q(drug_b__icontains=search_q) | 
            Q(reaction__name__icontains=search_q)
        )
        
    if min_severity and min_severity.isdigit():
        sev_val = int(min_severity)
        exact_sev = request.GET.get('exact_sev', '').strip().lower()
        if exact_sev == 'true':
            qs = qs.filter(severity_slider=sev_val)
        else:
            qs = qs.filter(severity_slider__gte=sev_val)

    sort_field = 'id'
    if sort_by == 'severity':
        sort_field = 'severity_slider'
    elif sort_by == 'drug_a':
        sort_field = 'drug_a'

    if order == 'desc':
        sort_field = '-' + sort_field
        sort_secondary = '-id'
    else:
        sort_secondary = 'id'

    if sort_field.strip('-') == 'id':
        qs = qs.order_by(sort_field)
    else:
        qs = qs.order_by(sort_field, sort_secondary)

    total_count = qs.count()
    start = (page - 1) * limit
    end = start + limit
    page_qs = qs[start:end]
    
    data = []
    for item in page_qs:
        data.append({
            'id': item.id,
            'drug_a': item.drug_a,
            'drug_b': item.drug_b,
            'reaction': item.reaction.name,
            'severity': item.severity_slider,
            'remedy': item.remedy,
            'time_window_hours': item.time_window_hours,
            'organ_bitmask': item.organ_bitmask,
            'custom_factors': item.custom_factors
        })
    from .models import Drug
    unique_drugs_count = Drug.objects.count()

    return Response({
        'total': total_count,
        'unique_drugs_count': unique_drugs_count,
        'page': page,
        'limit': limit,
        'total_pages': (total_count + limit - 1) // limit if total_count > 0 else 1,
        'interactions': data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def create_interaction(request):
    """Create a new custom interaction rule."""
    drug_a = request.data.get('drug_a', '').strip().lower()
    drug_b = request.data.get('drug_b', '').strip().lower()
    reaction_name = request.data.get('reaction', '').strip()
    severity = int(request.data.get('severity', 5))
    time_window_hours = int(request.data.get('time_window_hours', 24))
    remedy = request.data.get('remedy', '').strip()
    organ_bitmask = int(request.data.get('organ_bitmask', 0))
    custom_factors = request.data.get('custom_factors', {})

    if not drug_a or not drug_b or not reaction_name:
        return Response({'error': 'Drug A, Drug B, and Reaction text are required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Bidirectional Deduplication Algorithm (Sort alphabetically)
    d1, d2 = sorted([drug_a, drug_b])

    reaction_obj, _ = ReactionDefinition.objects.get_or_create(name=reaction_name)
    
    # Check for existing rule in either direction (A+B or B+A)
    existing = Interaction.objects.filter(
        (Q(drug_a=d1) & Q(drug_b=d2)) | (Q(drug_a=d2) & Q(drug_b=d1))
    ).first()

    if existing:
        existing.drug_a = d1
        existing.drug_b = d2
        existing.reaction = reaction_obj
        existing.severity_slider = severity
        existing.time_window_hours = time_window_hours
        existing.remedy = remedy
        existing.organ_bitmask = organ_bitmask
        existing.custom_factors = custom_factors
        existing.save()
        interaction = existing
    else:
        interaction = Interaction.objects.create(
            drug_a=d1,
            drug_b=d2,
            reaction=reaction_obj,
            severity_slider=severity,
            time_window_hours=time_window_hours,
            remedy=remedy,
            organ_bitmask=organ_bitmask,
            custom_factors=custom_factors
        )
    
    return Response({'message': 'Interaction rule saved & deduplicated successfully!', 'id': interaction.id}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def delete_interaction(request):
    """Delete a rule by ID."""
    rule_id = request.data.get('id')
    if not rule_id:
        return Response({'error': 'Rule ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
    Interaction.objects.filter(id=rule_id).delete()
    return Response({'message': 'Rule deleted successfully.'})


# ── 4. Dynamic Timeline Engine Solver ───────────────────────────────────────
def _evaluate_custom_factors(factors, age, gender, weight):
    """Evaluates demographic constraints."""
    if not factors:
        return True
    if age is not None:
        if 'min_age' in factors and age < factors['min_age']: return False
        if 'max_age' in factors and age > factors['max_age']: return False
    if weight is not None:
        if 'min_weight' in factors and weight < factors['min_weight']: return False
        if 'max_weight' in factors and weight > factors['max_weight']: return False
    if gender is not None and 'gender' in factors:
        if factors['gender'].lower() != 'all' and factors['gender'].lower() != gender.lower(): return False
    return True


@api_view(['POST'])
@permission_classes([AllowAny])
def check_timeline(request):
    """
    Sub-millisecond dynamic timeline engine solver.
    Accepts any number of drug intakes and evaluates interactions using a single BULK query.
    """
    intakes = request.data.get('intakes', [])
    age = request.data.get('age')
    gender = request.data.get('gender')
    weight = request.data.get('weight')

    if len(intakes) < 2:
        return Response({'warnings': []})

    # Step 1: Normalize drug names
    windows = []
    drug_names = set()
    for item in intakes:
        raw_name = item.get('drug_name', '').strip().lower()
        drug_name = re.sub(r'^\s*(\([+\-±]\)-?|\([RS]\)-?|[dl]-)', '', raw_name, flags=re.IGNORECASE).strip()
        
        timestamp = item.get('timestamp', '')
        try:
            intake_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except Exception:
            intake_time = datetime.now(timezone.utc)
            
        windows.append({
            'raw_name': raw_name,
            'clean_name': drug_name,
            'intake_time': intake_time
        })
        drug_names.add(drug_name)

    # Step 2: BULK QUERY to avoid N+1 crash
    # Fetch ALL possible interactions involving ANY of the drugs in the timeline
    all_possible_rules = Interaction.objects.select_related('reaction').filter(
        drug_a__in=drug_names, drug_b__in=drug_names
    )
    
    # Build a fast O(1) lookup dictionary in RAM
    rule_dict = {}
    for rule in all_possible_rules:
        # Save both directions for easy lookup
        rule_dict[(rule.drug_a, rule.drug_b)] = rule
        rule_dict[(rule.drug_b, rule.drug_a)] = rule

    warnings = []

    # Step 3: Evaluate all timeline pairs instantly in RAM
    for i in range(len(windows)):
        for j in range(i + 1, len(windows)):
            w1, w2 = windows[i], windows[j]
            n1, n2 = w1['clean_name'], w2['clean_name']
            
            time_diff_hours = abs((w1['intake_time'] - w2['intake_time']).total_seconds()) / 3600.0

            db_rule = rule_dict.get((n1, n2))
            
            # If the DB returned a rule, and the severity is > 0
            if db_rule and db_rule.severity_slider > 0:
                if time_diff_hours <= db_rule.time_window_hours:
                    
                    if _evaluate_custom_factors(db_rule.custom_factors, age, gender, weight):
                        warnings.append({
                            'drug_a': w1['raw_name'],
                            'drug_b': w2['raw_name'],
                            'reaction': db_rule.reaction.name if db_rule.reaction else "Unknown interaction",
                            'severity': db_rule.severity_slider,
                            'remedy': db_rule.remedy,
                            'organ_bitmask': db_rule.organ_bitmask,
                            'custom_factors': db_rule.custom_factors
                        })

    # Sort warnings by highest severity
    warnings.sort(key=lambda x: x.get('severity', 0), reverse=True)

    return Response({
        'warnings': warnings,
        'intakes_processed': len(intakes)
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def debug_db(request):
    from django.conf import settings
    db_config = settings.DATABASES['default']
    
    from .models import Interaction
    count = Interaction.objects.count()
    
    return Response({
        'engine': db_config['ENGINE'],
        'name': db_config['NAME'],
        'rules_count': count
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_drugs(request):
    """
    Returns ALL unique drug names from the pure Drug model instantly.
    """
    from .models import Drug
    matches = Drug.objects.values_list('name', flat=True)
    formatted_drugs = sorted([d.title() for d in matches if d])
    return Response(formatted_drugs, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_drugs(request):
    """
    Searches the pure Drug directory for unique drug names matching the query.
    """
    query = request.GET.get('q', '').strip().lower()
    
    if len(query) < 2:
        return Response([])

    from .models import Drug
    matches = Drug.objects.filter(name__icontains=query).values_list('name', flat=True)
    
    # Convert to Title Case for UI presentation and return top 20 matches
    formatted_drugs = sorted([d.title() for d in matches if query in d.lower()])[:20]
    
    return Response(formatted_drugs, status=status.HTTP_200_OK)
