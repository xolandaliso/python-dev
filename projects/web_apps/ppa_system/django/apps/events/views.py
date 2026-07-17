from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Event, EventStatus
from .serializers import EventSerializer


def _require_admin_for_write(request):
    """Returns a 403 Response if this is a write and the user isn't staff, else None."""
    if request.method not in permissions.SAFE_METHODS and not request.user.is_staff:
        return Response(status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def event_list_create(request):
    """
    GET /api/events/events/?status=&type=&search=  — any authenticated
    user (requirement 6). POST — admin only (events requirement 1).
    """
    if request.method == "POST":
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    qs = Event.objects.all()
    status_param = request.query_params.get("status")
    type_param = request.query_params.get("type")
    search = request.query_params.get("search")
    if status_param:
        qs = qs.filter(status=status_param)
    if type_param:
        qs = qs.filter(type=type_param)
    if search:
        qs = qs.filter(title__icontains=search)
    return Response(EventSerializer(qs, many=True).data)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def event_detail(request, pk):
    """GET — any authenticated user. PATCH/DELETE — admin only."""
    event = get_object_or_404(Event, pk=pk)
    forbidden = _require_admin_for_write(request)
    if forbidden:
        return forbidden

    if request.method == "GET":
        return Response(EventSerializer(event).data)
    if request.method == "DELETE":
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = EventSerializer(event, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def events_upcoming(request):
    """GET /api/events/events/upcoming/ — requirement 6."""
    qs = Event.objects.filter(date__gte=timezone.now().date(), status=EventStatus.OPEN)
    return Response(EventSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def event_close(request, pk):
    """
    POST /api/events/events/{id}/close/ — admin closes entries. Only
    flips status; the frontend calls the Go service's /seed endpoint
    next. Kept as two explicit calls rather than Django calling Go
    synchronously — see architecture notes in the project README.
    """
    event = get_object_or_404(Event, pk=pk)
    event.status = EventStatus.CLOSED
    event.save(update_fields=["status"])
    return Response(EventSerializer(event).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def event_complete(request, pk):
    """
    POST /api/events/events/{id}/complete/ — admin (or the frontend,
    right after Go's generate-times call resolves) marks the event
    COMPLETED, which unlocks the results view for members.
    """
    event = get_object_or_404(Event, pk=pk)
    event.status = EventStatus.COMPLETED
    event.save(update_fields=["status"])
    return Response(EventSerializer(event).data)