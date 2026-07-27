"""
Pharmacy Clinical Tracker – Full API Engine & Admin Console Views
================================================================
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from django.db.models import Q
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib.auth import authenticate

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
    """List all custom rules in database."""
    interactions = Interaction.objects.select_related('reaction').all()
    data = []
    for item in interactions:
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
    return Response({'interactions': data})


@api_view(['POST'])
@permission_classes([AllowAny])
def create_interaction(request):
    """Create a new custom interaction rule."""
    drug_a = request.data.get('drug_a', '').strip().lower()
    drug_b = request.data.get('drug_b', '').strip().lower()
    reaction_name = request.data.get('reaction', '').strip()
    severity = int(request.data.get('severity', 5))
    remedy = request.data.get('remedy', '').strip()
    organ_bitmask = int(request.data.get('organ_bitmask', 0))
    custom_factors = request.data.get('custom_factors', {})

    if not drug_a or not drug_b or not reaction_name:
        return Response({'error': 'Drug A, Drug B, and Reaction text are required.'}, status=status.HTTP_400_BAD_REQUEST)

    reaction_obj, _ = ReactionDefinition.objects.get_or_create(name=reaction_name)
    
    interaction, created = Interaction.objects.update_or_create(
        drug_a=drug_a,
        drug_b=drug_b,
        defaults={
            'reaction': reaction_obj,
            'severity_slider': severity,
            'remedy': remedy,
            'organ_bitmask': organ_bitmask,
            'custom_factors': custom_factors
        }
    )
    
    return Response({'message': 'Interaction rule saved successfully!', 'id': interaction.id}, status=status.HTTP_201_CREATED)


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
    Accepts any number of drug intakes and evaluates interactions.
    """
    intakes = request.data.get('intakes', [])
    age = request.data.get('age')
    gender = request.data.get('gender')
    weight = request.data.get('weight')

    if len(intakes) < 2:
        return Response({'warnings': []})

    # Step 1: Normalize drug names
    windows = []
    for item in intakes:
        raw_name = item.get('drug_name', '').strip().lower()
        # Clean stereoisomer prefixes like (+)-, (-)-, (±)-
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

    warnings = []

    # Step 2: Evaluate all pairs
    for i in range(len(windows)):
        for j in range(i + 1, len(windows)):
            w1, w2 = windows[i], windows[j]
            n1, n2 = w1['clean_name'], w2['clean_name']

            db_matches = Interaction.objects.select_related('reaction').filter(
                Q(drug_a=n1, drug_b=n2) | Q(drug_a=n2, drug_b=n1)
            )

            matched_interactions = []
            for db_rule in db_matches:
                matched_interactions.append({
                    'drug_a': w1['raw_name'],
                    'drug_b': w2['raw_name'],
                    'reaction': db_rule.reaction.name,
                    'severity': db_rule.severity_slider,
                    'remedy': db_rule.remedy,
                    'organ_bitmask': db_rule.organ_bitmask,
                    'custom_factors': db_rule.custom_factors
                })

            if matched_interactions:
                matched_interactions.sort(key=lambda x: x.get('severity', 0), reverse=True)
                top_rule = matched_interactions[0]
                
                if _evaluate_custom_factors(top_rule.get('custom_factors', {}), age, gender, weight):
                    warnings.append(top_rule)

    return Response({
        'warnings': warnings,
        'intakes_processed': len(intakes)
    }, status=status.HTTP_200_OK)