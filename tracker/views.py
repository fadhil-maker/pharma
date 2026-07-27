"""
Pharmacy Clinical Tracker – Clean Starter Views
==============================================
"""

import os
import json
import logging
from django.conf import settings
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
        return JsonResponse({"status": "Admin already exists! Log in with username: admin | password: adminpassword123"})
    
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword123')
    return JsonResponse({"status": "Success! Superuser created. Username: admin | Password: adminpassword123"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_profile(request):
    user = request.user
    return Response({
        'username': user.username,
        'email': user.email,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M'),
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else None,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def check_timeline(request):
    """
    Clean starter timeline analyzer endpoint.
    Preserves domain & hosting API connection: https://pharma.shanudigicore.com
    """
    intakes = request.data.get('intakes', [])
    age = request.data.get('age')
    gender = request.data.get('gender')
    weight = request.data.get('weight')

    warnings = []
    
    # Ready for custom business logic / new rule evaluation
    return Response({
        'warnings': warnings,
        'intakes_processed': len(intakes),
        'status': 'Clean Starter Endpoint Active'
    }, status=status.HTTP_200_OK)