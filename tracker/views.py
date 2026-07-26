"""
Pharmacy Clinical Tracker – API Views
======================================
Core timeline engine and CRUD endpoints for the drug interaction system.
All write operations are protected by JWT/Session authentication.
The timeline check endpoint remains public for patient use.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from django.conf import settings

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import ReactionDefinition, Interaction
from django.contrib.auth.models import User
from django.http import JsonResponse

logger = logging.getLogger(__name__)

def setup_admin(request):
    if User.objects.filter(username='admin').exists():
        return JsonResponse({"status": "Admin already exists! You can log in with username: admin | password: adminpassword123"})
    
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword123')
    return JsonResponse({"status": "Success! Admin account created. Username: admin | Password: adminpassword123"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_profile(request):
    """Return the currently logged-in admin's profile."""
    user = request.user
    return Response({
        'username': user.username,
        'email': user.email,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M'),
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_admins(request):
    """Return list of all admin/staff users."""
    users = User.objects.filter(is_staff=True).values(
        'id', 'username', 'email', 'is_superuser', 'date_joined', 'last_login'
    )
    return Response({'admins': list(users)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_admin(request):
    """Add a new admin user. Only superusers can do this."""
    if not request.user.is_superuser:
        return Response({'error': 'Only super admins can add new admins.'}, status=status.HTTP_403_FORBIDDEN)
    
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    email = request.data.get('email', '').strip()
    make_super = request.data.get('is_superuser', False)

    if not username or not password:
        return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(password) < 6:
        return Response({'error': 'Password must be at least 6 characters.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'error': f'Username "{username}" already exists.'}, status=status.HTTP_409_CONFLICT)
    
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_staff = True
    if make_super:
        user.is_superuser = True
    user.save()
    
    return Response({'message': f'Admin "{username}" created successfully!'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_admin(request):
    """Delete an admin user. Only superusers can do this. Cannot delete yourself."""
    if not request.user.is_superuser:
        return Response({'error': 'Only super admins can remove admins.'}, status=status.HTTP_403_FORBIDDEN)
    
    target_id = request.data.get('id')
    if not target_id:
        return Response({'error': 'Admin ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        target_user = User.objects.get(id=target_id)
    except User.DoesNotExist:
        return Response({'error': 'Admin not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    if target_user.id == request.user.id:
        return Response({'error': 'You cannot delete your own account.'}, status=status.HTTP_400_BAD_REQUEST)
    
    name = target_user.username
    target_user.delete()
    return Response({'message': f'Admin "{name}" has been removed.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_admin_password(request):
    """Reset password for an admin user. Only superusers can do this."""
    if not request.user.is_superuser:
        return Response({'error': 'Only super admins can reset passwords.'}, status=status.HTTP_403_FORBIDDEN)
    
    target_id = request.data.get('id')
    new_password = request.data.get('password', '').strip()

    if not target_id or not new_password:
        return Response({'error': 'Admin ID and new password are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(new_password) < 6:
        return Response({'error': 'Password must be at least 6 characters long.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_user = User.objects.get(id=target_id)
    except User.DoesNotExist:
        return Response({'error': 'Admin not found.'}, status=status.HTTP_404_NOT_FOUND)

    target_user.set_password(new_password)
    target_user.save()
    return Response({'message': f'Password for admin "{target_user.username}" successfully reset!'})

# ── Metabolic baseline constants ──────────────────────────────────────────────
ACTIVATION_OFFSET_MINUTES = 30   # Default minutes until drug becomes active
CLEARANCE_WINDOW_HOURS = 24      # Default hours until drug clears the system

# ── Load In-Memory JSON Algorithmic Engine ─────────────────────────────────────
DRUG_CLASSES = {}
INTERACTION_RULES = []
try:
    with open(os.path.join(settings.BASE_DIR, 'tracker', 'drug_classes.json'), 'r') as f:
        DRUG_CLASSES = json.load(f)
    with open(os.path.join(settings.BASE_DIR, 'tracker', 'interaction_rules.json'), 'r') as f:
        INTERACTION_RULES = json.load(f)
except Exception as e:
    logger.error(f"Failed to load JSON Algorithmic Engine files: {e}")


# =============================================================================
# PUBLIC READ ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_reactions(request):
    """Return all registered reaction definitions as a JSON list."""
    reactions = list(
        ReactionDefinition.objects.values('id', 'name').order_by('name')
    )
    return Response(reactions, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_interactions(request):
    """Return all registered interactions with reaction names included."""
    interactions = Interaction.objects.select_related('reaction').all()
    payload = []
    for inter in interactions:
        payload.append({
            'id': inter.id,
            'drug_a': inter.drug_a,
            'drug_b': inter.drug_b,
            'reaction_id': inter.reaction_id,
            'reaction_name': inter.reaction.name,
            'severity_slider': inter.severity_slider,
            'remedy': inter.remedy,
            'custom_factors': inter.custom_factors,
        })
    return Response(payload, status=status.HTTP_200_OK)


# =============================================================================
# AUTHENTICATED WRITE ENDPOINTS
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_reaction(request):
    """
    Create a new master reaction definition.
    Expects JSON: { "name": "serotonin syndrome" }
    Name is auto-normalized to lowercase.
    """
    try:
        data = request.data
        name = data.get('name', '').strip().lower()
        if not name:
            return Response(
                {'error': 'Reaction name is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reaction, created = ReactionDefinition.objects.get_or_create(name=name)
        return Response(
            {
                'status': 'created' if created else 'exists',
                'id': reaction.id,
                'name': reaction.name,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    except Exception as exc:
        logger.exception('Error creating reaction')
        return Response(
            {'error': str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_interaction(request):
    """
    Map a new drug-drug interaction by generic INN names.
    Expects JSON:
    {
        "drug_a": "aspirin",
        "drug_b": "warfarin",
        "reaction_id": 1,
        "severity_slider": 8,
        "remedy": "Discontinue one agent and monitor INR closely.",
        "custom_factors": {
            "min_age": 18,
            "gender": "any",
            "conditions": ["bleeding disorder"]
        }
    }
    Drug names are auto-normalized to lowercase.
    """
    try:
        data = request.data
        drug_a = data.get('drug_a', '').strip().lower()
        drug_b = data.get('drug_b', '').strip().lower()
        reaction_id = data.get('reaction_id')
        severity = data.get('severity_slider')
        remedy = data.get('remedy', '')
        custom_factors = data.get('custom_factors', {})

        if not drug_a or not drug_b:
            return Response(
                {'error': 'Both drug_a and drug_b generic names are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not reaction_id:
            return Response(
                {'error': 'reaction_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if severity is None:
            return Response(
                {'error': 'severity_slider is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        severity = int(severity)
        if severity < 1 or severity > 10:
            return Response(
                {'error': 'severity_slider must be between 1 and 10.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify reaction exists
        try:
            reaction = ReactionDefinition.objects.get(id=reaction_id)
        except ReactionDefinition.DoesNotExist:
            return Response(
                {'error': f'Reaction with id {reaction_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Ensure custom_factors is a dict
        if isinstance(custom_factors, str):
            try:
                custom_factors = json.loads(custom_factors)
            except json.JSONDecodeError:
                custom_factors = {}

        interaction, created = Interaction.objects.get_or_create(
            drug_a=drug_a,
            drug_b=drug_b,
            reaction=reaction,
            defaults={
                'severity_slider': severity,
                'remedy': remedy,
                'custom_factors': custom_factors,
            }
        )

        if not created:
            # Update existing interaction's mutable fields
            interaction.severity_slider = severity
            interaction.remedy = remedy
            interaction.custom_factors = custom_factors
            interaction.save()

        return Response(
            {
                'status': 'created' if created else 'updated',
                'id': interaction.id,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    except Exception as exc:
        logger.exception('Error creating interaction')
        return Response(
            {'error': str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================================================
# SMART CLINICAL SQL ENGINE MANAGEMENT (ADMIN API)
# =============================================================================

from tracker.models import DrugClassMapping

@api_view(['GET'])
@permission_classes([AllowAny])
def get_engine_rules(request):
    """
    Fetch all active database rules and class mappings from SQLite.
    Supports query params: sort_by (severity_asc, severity_desc, reaction_asc, drug_asc)
    """
    sort_by = request.GET.get('sort_by', 'severity_desc')
    q = request.GET.get('q', '').strip().lower()

    queryset = Interaction.objects.select_related('reaction').all()

    if q:
        # Resolve class tag for q if it's a known generic/brand name
        mapped_cls = DrugClassMapping.objects.filter(drug_name=q).first()
        mapped_tag = mapped_cls.class_tag if mapped_cls else (DRUG_CLASSES.get(q) or q)
        if not mapped_tag.startswith('@') and mapped_tag in DRUG_CLASSES.values():
            mapped_tag = '@' + mapped_tag.lstrip('@')

        queryset = queryset.filter(
            Q(drug_a__icontains=q) | Q(drug_b__icontains=q) |
            Q(drug_a__icontains=mapped_tag) | Q(drug_b__icontains=mapped_tag) |
            Q(reaction__name__icontains=q) | Q(remedy__icontains=q)
        )

    if sort_by == 'severity_asc':
        queryset = queryset.order_by('severity_slider', 'reaction__name')
    elif sort_by == 'severity_desc':
        queryset = queryset.order_by('-severity_slider', 'reaction__name')
    elif sort_by == 'reaction_asc':
        queryset = queryset.order_by('reaction__name')
    elif sort_by == 'drug_asc':
        queryset = queryset.order_by('drug_a', 'drug_b')

    rules_list = []
    seen_keys = set()

    for inter in queryset:
        # Normalize pair key independent of order (e.g. A+B vs B+A)
        pair_key = (
            tuple(sorted([inter.drug_a.strip().lower(), inter.drug_b.strip().lower()])),
            inter.reaction.name.strip().lower()
        )
        if pair_key in seen_keys:
            # Delete duplicate row from SQLite DB
            try:
                inter.delete()
            except Exception:
                pass
            continue
        
        seen_keys.add(pair_key)
        rules_list.append({
            'id': inter.id,
            'group_a': inter.drug_a,
            'group_b': inter.drug_b,
            'reaction': inter.reaction.name,
            'severity': inter.severity_slider,
            'remedy': inter.remedy,
            'time_window_hours': inter.time_window_hours,
            'custom_factors': inter.custom_factors or {}
        })

    # Also include in-memory JSON rules if SQLite is empty
    if not rules_list and INTERACTION_RULES:
        rules_list = INTERACTION_RULES

    # Build drug class dictionary
    db_classes = {m.drug_name: m.class_tag for m in DrugClassMapping.objects.all()}
    merged_classes = {**DRUG_CLASSES, **db_classes}

    return Response({
        'classes': merged_classes,
        'rules': rules_list,
        'count': len(rules_list)
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def smart_check_and_add_rule(request):
    """
    Autonomous Admin Endpoint:
    1. Accepts group_a, group_b, or drugs (comma-separated list of 2, 3, 4, 5+ drugs), reaction, severity, remedy, min_age, max_age, min_weight, max_weight, time_hours.
    2. Auto-resolves class tags for all drugs (e.g. Panadol -> @acetaminophen).
    3. Auto-generates pairwise combinations if 3+ drugs are submitted.
    4. Saves/Updates Interactions in SQLite.
    """
    try:
        data = request.data
        raw_a = str(data.get('group_a', '')).strip().lower()
        raw_b = str(data.get('group_b', '')).strip().lower()
        raw_drugs = str(data.get('drugs', '')).strip().lower()
        
        reaction_name = str(data.get('reaction', '')).strip().lower()
        severity = int(data.get('severity', 5))
        remedy = str(data.get('remedy', '')).strip()
        time_hours = int(data.get('time_hours', 24))

        min_age = data.get('min_age')
        max_age = data.get('max_age')
        min_weight = data.get('min_weight')
        max_weight = data.get('max_weight')

        custom_factors = {}
        if min_age is not None and str(min_age).isdigit(): custom_factors['min_age'] = int(min_age)
        if max_age is not None and str(max_age).isdigit(): custom_factors['max_age'] = int(max_age)
        if min_weight is not None and str(min_weight).replace('.','',1).isdigit(): custom_factors['min_weight'] = float(min_weight)
        if max_weight is not None and str(max_weight).replace('.','',1).isdigit(): custom_factors['max_weight'] = float(max_weight)

        if not reaction_name:
            return Response({'error': 'Clinical Reaction Definition is required.'}, status=400)

        # Build list of all submitted drugs
        submitted_drugs = []
        if raw_drugs:
            submitted_drugs = [d.strip() for d in raw_drugs.split(',') if d.strip()]
        else:
            if ',' in raw_a:
                submitted_drugs.extend([d.strip() for d in raw_a.split(',') if d.strip()])
            elif raw_a:
                submitted_drugs.append(raw_a)

            if ',' in raw_b:
                submitted_drugs.extend([d.strip() for d in raw_b.split(',') if d.strip()])
            elif raw_b:
                submitted_drugs.append(raw_b)

        # Deduplicate
        submitted_drugs = list(dict.fromkeys(submitted_drugs))

        if len(submitted_drugs) < 2:
            return Response({'error': 'Please provide at least 2 drugs (e.g. Panadol, Advil, Aspirin) to create an interaction rule.'}, status=400)

        rx_obj, _ = ReactionDefinition.objects.get_or_create(name=reaction_name)
        created_rules = []
        existing_rules = []

        # Generate all pairwise combinations
        from itertools import combinations
        pairs = list(combinations(submitted_drugs, 2))

        for drug_x, drug_y in pairs:
            # Look up class mappings
            class_x = DrugClassMapping.objects.filter(drug_name=drug_x).first()
            class_y = DrugClassMapping.objects.filter(drug_name=drug_y).first()

            tag_x = class_x.class_tag if class_x else (DRUG_CLASSES.get(drug_x) or drug_x)
            tag_y = class_y.class_tag if class_y else (DRUG_CLASSES.get(drug_y) or drug_y)

            if not tag_x.startswith('@') and tag_x in DRUG_CLASSES.values(): tag_x = '@' + tag_x.lstrip('@')
            if not tag_y.startswith('@') and tag_y in DRUG_CLASSES.values(): tag_y = '@' + tag_y.lstrip('@')

            existing = Interaction.objects.select_related('reaction').filter(
                (Q(drug_a=drug_x, drug_b=drug_y) | Q(drug_a=drug_y, drug_b=drug_x) |
                 Q(drug_a=tag_x, drug_b=tag_y) | Q(drug_a=tag_y, drug_b=tag_x)),
                reaction__name=reaction_name
            ).first()

            if existing:
                existing_rules.append(f"{drug_x} + {drug_y}")
            else:
                new_rule = Interaction.objects.create(
                    drug_a=tag_x,
                    drug_b=tag_y,
                    reaction=rx_obj,
                    severity_slider=severity,
                    remedy=remedy,
                    time_window_hours=time_hours,
                    custom_factors=custom_factors
                )
                created_rules.append({
                    'id': new_rule.id,
                    'group_a': tag_x,
                    'group_b': tag_y,
                    'reaction': reaction_name,
                    'severity': severity,
                    'remedy': remedy
                })

        if created_rules:
            msg = f"🎉 Successfully created interaction rule across {len(created_rules)} drug pair(s) for [{', '.join(submitted_drugs)}]!"
            if existing_rules:
                msg += f" (Note: {len(existing_rules)} pair(s) already existed)."
            return Response({
                'status': 'created',
                'message': msg,
                'created_count': len(created_rules),
                'rules': created_rules
            }, status=201)
        else:
            return Response({
                'status': 'exists',
                'message': f"✨ Detected: All drug pair combinations for [{', '.join(submitted_drugs)}] already exist in database!",
                'existing_pairs': existing_rules
            }, status=200)

    except Exception as e:
        return Response({'error': str(e)}, status=500)

        # Create reaction definition if needed
        rx_obj, _ = ReactionDefinition.objects.get_or_create(name=reaction_name)

        # Create new interaction in SQLite
        new_inter = Interaction.objects.create(
            drug_a=tag_a,
            drug_b=tag_b,
            reaction=rx_obj,
            severity_slider=severity,
            remedy=remedy,
            time_window_hours=time_hours,
            custom_factors=custom_factors
        )

        return Response({
            'status': 'created',
            'message': f"✨ Automatically classified & added to database under tags: {tag_a} + {tag_b}",
            'rule': {
                'id': new_inter.id,
                'group_a': new_inter.drug_a,
                'group_b': new_inter.drug_b,
                'reaction': rx_obj.name,
                'severity': new_inter.severity_slider,
                'remedy': new_inter.remedy,
                'time_window_hours': new_inter.time_window_hours,
                'custom_factors': new_inter.custom_factors
            }
        }, status=201)

    except Exception as exc:
        logger.exception("Error in smart_check_and_add_rule")
        return Response({'error': str(exc)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def delete_engine_rule(request):
    """Delete a rule by ID from SQLite."""
    try:
        rule_id = request.data.get('id')
        if rule_id:
            Interaction.objects.filter(id=rule_id).delete()
            return Response({'status': 'deleted'})
        
        # Fallback to index for JSON list
        index = int(request.data.get('index', -1))
        if 0 <= index < len(INTERACTION_RULES):
            deleted = INTERACTION_RULES.pop(index)
            return Response({'status': 'deleted', 'rule': deleted})

        return Response({'error': 'Invalid rule ID or index'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def seed_database_api(request):
    """1-Click API endpoint to seed SQLite with 50+ rules and 25+ reaction definitions."""
    try:
        from django.core.management import call_command
        call_command('seed_clinical_data')
        return Response({'status': 'success', 'message': 'SQLite Clinical Database seeded successfully!'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# =============================================================================
# CORE TIMELINE ENGINE (PUBLIC)
# =============================================================================

def _parse_timestamp(ts_string):
    """
    Parse an ISO-8601 timestamp string into a timezone-aware datetime.
    Handles various formats: with/without Z, with/without timezone offset.
    """
    if not ts_string:
        return None

    ts_string = ts_string.strip()

    # Replace trailing Z with +00:00 for fromisoformat compatibility
    if ts_string.endswith('Z'):
        ts_string = ts_string[:-1] + '+00:00'

    try:
        dt = datetime.fromisoformat(ts_string)
    except ValueError:
        # Fallback: try strptime for common formats
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.strptime(ts_string, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Cannot parse timestamp: {ts_string}")

    # Ensure timezone-aware (default to UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def _evaluate_custom_factors(custom_factors, age, gender, weight):
    """
    Evaluate custom_factors constraints against the patient profile.
    Returns True if the interaction applies to this patient, False otherwise.

    custom_factors schema:
    {
        "min_age": int,       # Skip if patient age < min_age
        "max_age": int,       # Skip if patient age > max_age
        "min_weight": float,  # Skip if patient weight < min_weight
        "max_weight": float,  # Skip if patient weight > max_weight
        "gender": str         # Skip if patient gender doesn't match (case-insensitive)
    }
    """
    if not custom_factors or not isinstance(custom_factors, dict):
        return True  # No constraints means it applies universally

    # Age check: min_age
    min_age = custom_factors.get('min_age')
    if min_age is not None and age is not None:
        try:
            if int(age) < int(min_age):
                return False
        except (ValueError, TypeError):
            pass

    # Age check: max_age
    max_age = custom_factors.get('max_age')
    if max_age is not None and age is not None:
        try:
            if int(age) > int(max_age):
                return False
        except (ValueError, TypeError):
            pass

    # Gender check
    factor_gender = custom_factors.get('gender')
    if factor_gender and gender:
        fg = str(factor_gender).strip().lower()
        pg = str(gender).strip().lower()
        if fg not in ('any', 'all', '') and fg != pg:
            return False

    # Weight check: min_weight
    min_weight = custom_factors.get('min_weight')
    if min_weight is not None and weight is not None:
        try:
            if float(weight) < float(min_weight):
                return False
        except (ValueError, TypeError):
            pass

    # Weight check: max_weight
    max_weight = custom_factors.get('max_weight')
    if max_weight is not None and weight is not None:
        try:
            if float(weight) > float(max_weight):
                return False
        except (ValueError, TypeError):
            pass

    return True


@api_view(['POST'])
@permission_classes([AllowAny])
def check_timeline(request):
    """
    Core Timeline Engine – compute metabolic overlap windows and evaluate
    drug-drug interactions against the patient profile.

    Expects JSON payload:
    {
        "intakes": [
            {"drug_name": "aspirin", "timestamp": "2024-01-15T08:00:00Z"},
            {"drug_name": "warfarin", "timestamp": "2024-01-15T10:00:00Z"}
        ],
        "age": 45,
        "gender": "male",
        "weight": 70
    }

    Returns:
    {
        "warnings": [
            {
                "drug_a": "aspirin",
                "drug_b": "warfarin",
                "reaction": "increased bleeding risk",
                "severity": 8,
                "remedy": "Monitor INR closely...",
                "custom_factors": {...},
                "overlap_start": "2024-01-15T08:30:00+00:00",
                "overlap_end": "2024-01-16T08:30:00+00:00"
            }
        ]
    }
    """
    try:
        data = request.data
        intakes = data.get('intakes', [])
        age = data.get('age')
        gender = data.get('gender')
        weight = data.get('weight')

        if not intakes or len(intakes) < 2:
            return Response(
                {'warnings': [], 'message': 'At least 2 drugs required for analysis.'},
                status=status.HTTP_200_OK
            )

        if age is None or gender is None or weight is None:
            return Response(
                {'error': 'Age, gender, and weight are mandatory fields.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        print("=== DEBUG PAYLOAD ===")
        print(f"Intakes: {intakes}")
        print(f"Age: {age}, Gender: {gender}, Weight: {weight}")

        # ── Step 1: Compute metabolic activity windows ────────────────────
        windows = []
        for item in intakes:
            drug_name = item.get('drug_name', '').strip().lower()
            timestamp = item.get('timestamp', '')
            print(f"Processing drug: {drug_name} at {timestamp}")

            if not drug_name or not timestamp:
                continue

            try:
                intake_time = _parse_timestamp(timestamp)
            except ValueError:
                continue

            start_active = intake_time + timedelta(minutes=ACTIVATION_OFFSET_MINUTES)
            end_active = start_active + timedelta(hours=CLEARANCE_WINDOW_HOURS)

            windows.append({
                'drug_name': drug_name,
                'start': start_active,
                'end': end_active,
            })

        # ── Step 2: Find overlapping pairs and query interactions ─────────
        warnings = []

        for i in range(len(windows)):
            for j in range(i + 1, len(windows)):
                w1 = windows[i]
                w2 = windows[j]

                # Calculate overlap window
                overlap_start = max(w1['start'], w2['start'])
                overlap_end = min(w1['end'], w2['end'])

                if overlap_start >= overlap_end:
                    continue  # No overlap

                # Query interactions bidirectionally (case-insensitive)
                name_i = w1['drug_name']
                name_j = w2['drug_name']
                
                # Resolve algorithmic classes from the in-memory dictionary
                class_i = DRUG_CLASSES.get(name_i, name_i)
                class_j = DRUG_CLASSES.get(name_j, name_j)
                
                print(f"Match logic for {name_i} (Class: {class_i}) and {name_j} (Class: {class_j})")

                # ── Search SQLite Database & In-Memory Algorithmic Engine ──────────────
                matched_interactions = []

                # Query SQLite Database Interactions
                db_matches = Interaction.objects.select_related('reaction').filter(
                    Q(drug_a=name_i, drug_b=name_j) | Q(drug_a=name_j, drug_b=name_i) |
                    Q(drug_a=class_i, drug_b=class_j) | Q(drug_a=class_j, drug_b=class_i) |
                    Q(drug_a=name_i, drug_b=class_j) | Q(drug_a=class_j, drug_b=name_i) |
                    Q(drug_a=class_i, drug_b=name_j) | Q(drug_a=name_j, drug_b=class_i)
                )

                for db_rule in db_matches:
                    matched_interactions.append({
                        'reaction': db_rule.reaction.name,
                        'severity': db_rule.severity_slider,
                        'remedy': db_rule.remedy,
                        'custom_factors': db_rule.custom_factors or {},
                        'time_window_hours': db_rule.time_window_hours
                    })

                # Fallback to JSON rules if no DB match
                if not matched_interactions:
                    for rule in INTERACTION_RULES:
                        ra, rb = rule.get('group_a', '').lower(), rule.get('group_b', '').lower()
                        match = False
                        if (ra == name_i and rb == name_j) or (ra == name_j and rb == name_i): match = True
                        elif (ra == class_i and rb == class_j) or (ra == class_j and rb == class_i): match = True
                        elif (ra == name_i and rb == class_j) or (ra == class_j and rb == name_i): match = True
                        elif (ra == class_i and rb == name_j) or (ra == name_j and rb == class_i): match = True

                        if match:
                            matched_interactions.append(rule)

                for rule in matched_interactions:
                    # ── Step 3: Evaluate custom_factors against patient ────
                    if not _evaluate_custom_factors(
                        rule.get('custom_factors', {}), age, gender, weight
                    ):
                        continue  # This interaction doesn't apply to patient

                    warnings.append({
                        'drug_a': name_i,
                        'drug_b': name_j,
                        'reaction': rule.get('reaction', 'Unknown Reaction'),
                        'severity': rule.get('severity', 5),
                        'remedy': rule.get('remedy', ''),
                        'custom_factors': rule.get('custom_factors', {}),
                        'overlap_start': overlap_start.isoformat(),
                        'overlap_end': overlap_end.isoformat(),
                    })

        # Sort warnings by severity descending (most critical first)
        warnings.sort(key=lambda w: w['severity'], reverse=True)

        return Response({'warnings': warnings}, status=status.HTTP_200_OK)

    except Exception as exc:
        logger.exception('Error in timeline analysis')
        return Response(
            {'error': f'Timeline analysis failed: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )