from django.db import models
from django.contrib.auth.models import User



class MetaInfo(models.Model):
    class Meta:
        abstract = True
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AddressZone(MetaInfo):
    name = models.CharField(max_length=100)

    organization = models.ForeignKey("organizations.Organization",
                                     on_delete=models.CASCADE,
                                     related_name="zones")
    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_zone_per_organization")
        ]
                                    



class CustomerProfile(MetaInfo):
    CUSTOMER_STATUS_CHOICES = [
        ("active", "Active - Connected"),
        ("disconnected", "Disconnected"),
        ("free", "Free / Complimentary"),
        ("left", "Left / Churned"),
    ]

    organization = models.ForeignKey(
    "organizations.Organization",
    on_delete=models.CASCADE,
    related_name="customers")

    customer_id = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=255)
    nid = models.CharField(max_length=15, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    phone_number2 = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=255)
    zone = models.ForeignKey(AddressZone, on_delete=models.CASCADE)
    package = models.ForeignKey("billing.Package", on_delete=models.SET_NULL, null=True, blank=True)
    billing_date = models.DateField(null=True, blank=True)
    customer_status = models.CharField(max_length=15, choices=CUSTOMER_STATUS_CHOICES, default="active")
    extended_billing_days = models.IntegerField(default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        ordering = ["customer_id"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "customer_id"], name="unique_customer_id_per_organization")
        ]



class SupportTicket(MetaInfo):
    TICKET_STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    TICKET_PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=TICKET_STATUS_CHOICES, default="open")
    priority = models.CharField(max_length=20, choices=TICKET_PRIORITY_CHOICES, default="medium")
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="support_tickets")


class TicketReply(MetaInfo):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="replies")
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ticket_replies")
    customer = models.ForeignKey(CustomerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="ticket_replies")
    reply_text = models.TextField()

    def __str__(self):
        author = self.admin_user.username if self.admin_user else self.customer.customer_name
        return f"Reply by {author} on Ticket #{self.ticket.id}"

    class Meta:
        ordering = ["created_at"]


