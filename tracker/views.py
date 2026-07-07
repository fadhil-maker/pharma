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

logger = logging.getLogger(__name__)

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

                # ── Search In-Memory JSON Algorithmic Engine ──────────────
                matched_interactions = []
                for rule in INTERACTION_RULES:
                    ra, rb = rule.get('group_a', '').lower(), rule.get('group_b', '').lower()
                    
                    # Check bidirectional match across generic name AND abstract class
                    match = False
                    if (ra == name_i and rb == name_j) or (ra == name_j and rb == name_i):
                        match = True
                    elif (ra == class_i and rb == class_j) or (ra == class_j and rb == class_i):
                        match = True
                    elif (ra == name_i and rb == class_j) or (ra == class_j and rb == name_i):
                        match = True
                    elif (ra == class_i and rb == name_j) or (ra == name_j and rb == class_i):
                        match = True
                        
                    if match:
                        print(f"Matched Rule: {ra} + {rb}")
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