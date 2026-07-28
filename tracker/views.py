"""
Pharmacy Clinical Tracker – Full API Engine & Admin Console Views
================================================================
"""

import os
import json
import logging
import re
import urllib.request
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

    sort_secondary = '-id' if order == 'desc' else 'id'
    if order == 'desc':
        sort_field = '-' + sort_field

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
    # Calculate true count of unique registered drugs
    unique_drugs_count = Interaction.objects.values_list('drug_a', flat=True).union(
        Interaction.objects.values_list('drug_b', flat=True)
    ).count()

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
            
            # Calculate time difference in hours
            time_diff_hours = abs((w1['intake_time'] - w2['intake_time']).total_seconds()) / 3600.0

            db_matches = Interaction.objects.select_related('reaction').filter(
                Q(drug_a=n1, drug_b=n2) | Q(drug_a=n2, drug_b=n1)
            )

            matched_interactions = []
            for db_rule in db_matches:
                # Strictly enforce time_window_hours constraint
                if time_diff_hours > db_rule.time_window_hours:
                    continue
                    
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

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_drugs(request):
    """
    Returns ALL unique drug names instantly (cached for 24 hours).
    Perfect for 0ms frontend autocomplete.
    """
    cached_drugs = cache.get('all_unique_drugs')
    if cached_drugs:
        return Response(cached_drugs, status=status.HTTP_200_OK)

    matches_a = Interaction.objects.values_list('drug_a', flat=True).distinct()
    matches_b = Interaction.objects.values_list('drug_b', flat=True).distinct()
    
    unique_drugs = set(matches_a).union(set(matches_b))
    formatted_drugs = sorted([d.title() for d in unique_drugs if d])
    
    cache.set('all_unique_drugs', formatted_drugs, timeout=86400) # 24 hours
    return Response(formatted_drugs, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_drugs(request):
    """
    Searches the massive interaction database for unique drug names matching the query.
    """
    query = request.GET.get('q', '').strip().lower()
    
    if len(query) < 2:
        return Response([])

    # Fast indexed search on drug_a and drug_b
    matches_a = Interaction.objects.filter(drug_a__icontains=query).values_list('drug_a', flat=True)
    matches_b = Interaction.objects.filter(drug_b__icontains=query).values_list('drug_b', flat=True)
    
    # Combine and deduplicate
    unique_drugs = set(matches_a).union(set(matches_b))
    
    # Convert to Title Case for UI presentation and return top 20 matches
    formatted_drugs = sorted([d.title() for d in unique_drugs if query in d.lower()])[:20]
    
    return Response(formatted_drugs, status=status.HTTP_200_OK)


# ── 5. Real-Time Smart Fetch (RxNorm API + Gemini AI) ──────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def smart_fetch_drug_interactions(request):
    """
    Connects to official NIH RxNorm API to fetch real-world interaction data.
    Optionally enhances severity and remedies using Gemini API if key is present.
    Injects structured interaction rules directly into PostgreSQL.
    """
    drug_name = request.data.get('drug_name', '').strip().lower()
    if not drug_name:
        return Response({'error': 'Drug name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Step 1: Fetch RxCUI code from NIH RxNav API
        rxcui_url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={urllib.parse.quote(drug_name)}"
        req = urllib.request.Request(rxcui_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            id_group = data.get('idGroup', {})
            rxnorm_ids = id_group.get('rxnormId', [])
            if not rxnorm_ids:
                return Response({'error': f"No official RxNorm concept found for '{drug_name}'."}, status=status.HTTP_404_NOT_FOUND)
            rxcui = rxnorm_ids[0]

        # Step 2: Query RxNorm Interaction API
        int_url = f"https://rxnav.nlm.nih.gov/REST/interaction/interaction.json?rxcui={rxcui}"
        req2 = urllib.request.Request(int_url, headers={'User-Agent': 'Mozilla/5.0'})
        raw_interactions = []
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            data2 = json.loads(resp2.read().decode())
            interaction_type_group = data2.get('interactionTypeGroup', [])
            for group in interaction_type_group:
                for int_type in group.get('interactionType', []):
                    for pair in int_type.get('interactionPair', []):
                        min_concept = pair.get('interactionConcept', [])
                        other_drug = ""
                        if len(min_concept) > 1:
                            other_drug = min_concept[1].get('minConceptItem', {}).get('name', '')
                        elif len(min_concept) == 1:
                            other_drug = min_concept[0].get('minConceptItem', {}).get('name', '')
                        
                        desc = pair.get('description', '')
                        if other_drug and desc:
                            raw_interactions.append({
                                'drug_b': other_drug.lower(),
                                'description': desc
                            })

        if not raw_interactions:
            return Response({'message': f"RxNorm concept exists, but no interaction pairs were found for '{drug_name}'."}, status=status.HTTP_200_OK)

        # Step 3: Save top 15 interactions
        saved_count = 0
        gemini_api_key = os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)

        for item in raw_interactions[:15]:
            drug_b = item['drug_b']
            desc = item['description']
            
            sev_score = 7 if 'severe' in desc.lower() or 'fatal' in desc.lower() else (4 if 'moderate' in desc.lower() else 5)
            remedy_text = f"Monitor patient closely when taking {drug_name} with {drug_b}."
            organ_bitmask = 16

            if 'liver' in desc.lower() or 'hepatic' in desc.lower(): organ_bitmask |= 16
            if 'kidney' in desc.lower() or 'renal' in desc.lower(): organ_bitmask |= 256
            if 'heart' in desc.lower() or 'cardiac' in desc.lower(): organ_bitmask |= 8
            if 'brain' in desc.lower() or 'cns' in desc.lower(): organ_bitmask |= 1
            if 'lung' in desc.lower() or 'respiratory' in desc.lower(): organ_bitmask |= 4

            if gemini_api_key:
                try:
                    prompt = f"Analyze this interaction between {drug_name} and {drug_b}: '{desc}'. Return JSON with: severity (1-10 int), cause (1 sentence), remedy (1 sentence)."
                    g_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
                    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
                    g_req = urllib.request.Request(g_url, data=payload, headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(g_req, timeout=5) as g_resp:
                        g_data = json.loads(g_resp.read().decode())
                        res_text = g_data['candidates'][0]['content']['parts'][0]['text']
                        match = re.search(r'\{.*\}', res_text, re.DOTALL)
                        if match:
                            parsed = json.loads(match.group())
                            sev_score = parsed.get('severity', sev_score)
                            desc = parsed.get('cause', desc)
                            remedy_text = parsed.get('remedy', remedy_text)
                except Exception:
                    pass

            d1, d2 = sorted([drug_name, drug_b])
            rx_obj, _ = ReactionDefinition.objects.get_or_create(name=desc[:500])

            existing = Interaction.objects.filter(
                (Q(drug_a=d1) & Q(drug_b=d2)) | (Q(drug_a=d2) & Q(drug_b=d1))
            ).first()

            if existing:
                existing.drug_a = d1
                existing.drug_b = d2
                existing.reaction = rx_obj
                existing.severity_slider = sev_score
                existing.remedy = remedy_text
                existing.organ_bitmask = organ_bitmask
                existing.save()
            else:
                Interaction.objects.create(
                    drug_a=d1,
                    drug_b=d2,
                    reaction=rx_obj,
                    severity_slider=sev_score,
                    time_window_hours=24,
                    remedy=remedy_text,
                    organ_bitmask=organ_bitmask
                )
            saved_count += 1

        return Response({
            'message': f"Successfully fetched and saved {saved_count} official RxNorm interactions for '{drug_name}' into PostgreSQL database!",
            'count': saved_count
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': f"Failed to fetch RxNorm data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
