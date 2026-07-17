from django.urls import path

from .views import (
    event_close, event_complete,
    event_detail, event_list_create, events_upcoming
)

urlpatterns = [
    path("events/", event_list_create, name="event-list-create"),
    path("events/upcoming/", events_upcoming, name="event-upcoming"),
    path("events/<int:pk>/", event_detail, name="event-detail"),
    path("events/<int:pk>/close/", event_close, name="event-close"),
    path("events/<int:pk>/complete/", event_complete, name="event-complete"),
]