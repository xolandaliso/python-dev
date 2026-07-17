from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Profile, Subscription
from .permissions import HasInternalServiceSecret, IsSelfOrAdmin
from .serializers import (
    CustomTokenObtainPairSerializer,
    MemberCardSerializer,
    ProfileSerializer,
    RegistrationSerializer,
    SubscriptionSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register_view(request):
    """POST /api/accounts/register/ — requirement 2: join/register."""
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    profile = serializer.save()
    return Response(ProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def profile_list(request):
    """
    GET /api/accounts/profiles/?search=...
    Admins list/search all members (requirement 8); a member gets back
    a single-item list containing only their own profile.
    """
    if request.user.is_staff:
        qs = Profile.objects.select_related("user").all()
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(surname__icontains=search)
                | Q(user__email__icontains=search)
            )
    else:
        qs = Profile.objects.filter(user=request.user)
    return Response(ProfileSerializer(qs, many=True).data)


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated, IsSelfOrAdmin])
def profile_detail(request, pk):
    """GET/PATCH /api/accounts/profiles/<pk>/ — requirement 3."""
    profile = get_object_or_404(Profile, pk=pk)
    # DRF applies object-level permissions automatically in generic
    # views, but a plain function view has to call this explicitly.
    if not IsSelfOrAdmin().has_object_permission(request, None, profile):
        return Response(status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        return Response(ProfileSerializer(profile).data)

    serializer = ProfileSerializer(profile, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def profile_me(request):
    """GET /api/accounts/profiles/me/ — requirement 3."""
    profile = get_object_or_404(Profile, user=request.user)
    return Response(ProfileSerializer(profile).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def profile_card(request):
    """GET /api/accounts/profiles/card/ — requirement 4."""
    profile = get_object_or_404(Profile, user=request.user)
    return Response(MemberCardSerializer(profile).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def subscription_list(request):
    """Members see their own subscription history; admins see all."""
    if request.user.is_staff:
        qs = Subscription.objects.select_related("user").all()
    else:
        qs = Subscription.objects.filter(user=request.user)
    return Response(SubscriptionSerializer(qs, many=True).data)


# innternal API — called only by the Go service, not React

@api_view(["GET", "PATCH"])
@permission_classes([HasInternalServiceSecret])
def internal_member_avg_time(request, member_id):
    """
    /internal/members/<id>/avg-time/ — GET returns the current average
    for seeding; PATCH writes the recomputed average after a race.
    """
    profile = get_object_or_404(Profile, user_id=member_id)

    if request.method == "GET":
        return Response({"average_race_time_seconds": profile.average_race_time_seconds})

    value = request.data.get("average_race_time_seconds")
    if value is None:
        return Response({"detail": "average_race_time_seconds is required"}, status=400)
    profile.average_race_time_seconds = value
    profile.save(update_fields=["average_race_time_seconds"])
    return Response({"average_race_time_seconds": profile.average_race_time_seconds})