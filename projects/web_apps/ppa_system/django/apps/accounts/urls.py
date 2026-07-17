from django.urls import path

from .views import (
    internal_member_avg_time,
    profile_card,
    profile_detail,
    profile_list,
    profile_me,
    register_view,
    subscription_list,
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("profiles/", profile_list, name="profile-list"),
    path("profiles/me/", profile_me, name="profile-me"),
    path("profiles/card/", profile_card, name="profile-card"),
    path("profiles/<int:pk>/", profile_detail, name="profile-detail"),
    path("subscriptions/", subscription_list, name="subscription-list"),
]

# Mounted separately under /internal/ in ppa_project/urls.py.
internal_urlpatterns = [
    path("members/<int:member_id>/avg-time/", internal_member_avg_time, name="internal-member-avg-time"),
]