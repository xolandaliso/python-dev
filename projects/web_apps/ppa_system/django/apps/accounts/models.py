from datetime import date
from django.conf import settings
from django.db import models

class Category(models.TextChoices):
    JUNIOR = "JUNIOR", "Junior"
    SENIOR = "SENIOR", "Senior"
    MASTER = "MASTER", "Master"
    VETERAN = "VETERAN", "Veteran"


class Profile(models.Model):
    """
    Extends Django's built-in User with PPA-specific membership data.
    is_staff/is_superuser on User already gives us the admin/member
    role split, so no separate role field is needed here.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    category = models.CharField(max_length=20, choices=Category.choices)

    # Persisted rather than computed on demand: this is the field the
    # Go seeding/timing service reads via the internal API
    # (GET /internal/members/{id}/avg-time) and writes back to after
    # each race. Seconds, so it's cheap to store/compare/sort on.
    average_race_time_seconds = models.PositiveIntegerField(null=True, blank=True)

    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.name} {self.surname}"

    def category_for_age(self, as_of: date | None = None) -> str:
        """
        Design decision: category is stored on the profile (not derived
        on every read) so it can be edited manually if needed, but this
        helper computes what it *should* be from date_of_birth. Wire it
        into a save() override or an annual management command,
        depending on whether PPA wants categories to shift automatically
        each year or stay locked at registration.
        """
        as_of = as_of or date.today()
        age = as_of.year - self.date_of_birth.year - (
            (as_of.month, as_of.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        if age < 19:
            return Category.JUNIOR
        if age < 40:
            return Category.SENIOR
        if age < 50:
            return Category.MASTER
        return Category.VETERAN


class PaymentStatus(models.TextChoices):
    NOT_APPLICABLE = "N_A", "Not applicable"
    UNPAID = "UNPAID", "Unpaid"
    PAID = "PAID", "Paid"


class Subscription(models.Model):
    """
    Kept separate from Profile (rather than a single expiry_date field)
    so renewal history is preserved and payment fields have somewhere
    natural to live once payments are added in a later iteration.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    membership_type = models.CharField(max_length=20, default="INDIVIDUAL")
    start_date = models.DateField()
    expiry_date = models.DateField()

    # Unused this iteration, but the field exists so payment can be
    # slotted in without a schema change later.
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.NOT_APPLICABLE
    )

    # Flips to True once the 30-day-before-expiry reminder has fired,
    # so the notification job doesn't re-send it every day.
    reminder_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expiry_date"]

    def __str__(self):
        return f"{self.user} — expires {self.expiry_date}"

    @property
    def is_active(self) -> bool:
        return self.expiry_date >= date.today()