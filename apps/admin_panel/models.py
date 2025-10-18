from django.db import models


class DoctorComplaint(models.Model):
    TYPES = (
        ("general", "General"),
        ("service", "Service"),
        ("billing", "Billing"),
    )
    STATUS = (
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    )
    PRIORITY = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    )
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE, related_name="complaints")
    subject = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    complaint_type = models.CharField(max_length=50, choices=TYPES, default="service")
    status = models.CharField(max_length=50, choices=STATUS, default="in_progress")
    priority = models.CharField(max_length=50, choices=PRIORITY, default="low")
    resolution_notes = models.TextField(null=True, blank=True)
    # transaction_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.subject

    def save(self, *args, **kwargs):
        if self.complaint_type == "billing":
            self.priority = "urgent"
        elif self.complaint_type == "general":
            self.priority = "low"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Doctor Complaint"
        verbose_name_plural = "Doctor Complaints"
        db_table = "doctor_complaint"

class DoctorComplaintFile(models.Model):
    complaint = models.ForeignKey(DoctorComplaint, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="complaint_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for {self.complaint.subject}"

    class Meta:
        verbose_name = "Doctor Complaint File"
        verbose_name_plural = "Doctor Complaint Files"
        db_table = "doctor_complaint_file"


class UserComplaint(models.Model):
    """Model for user complaints about doctors that will be visible in admin panel"""

    TYPES = (
        ("wrong_information", "Wrong Information"),
        ("fake_credentials", "Fake Credentials"),
        ("unprofessional_behavior", "Unprofessional Behavior"),
        ("pricing_issue", "Pricing Issue"),
        ("other", "Other"),
    )

    STATUS = (
        ("pending", "Kutilmoqda / Pending"),
        ("in_progress", "Jarayonda / In Progress"),
        ("resolved", "Hal qilindi / Resolved"),
        ("closed", "Yopildi / Closed"),
    )

    PRIORITY = (
        ("low", "Past / Low"),
        ("medium", "O'rtacha / Medium"),
        ("high", "Yuqori / High"),
        ("urgent", "Shoshilinch / Urgent"),
    )

    # User who created the complaint
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="user_complaints",
        verbose_name="Foydalanuvchi"
    )

    # Doctor being complained about
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="user_complaints",
        verbose_name="Shifokor"
    )

    # Complaint details
    subject = models.CharField(
        max_length=255,
        verbose_name="Mavzu"
    )

    description = models.TextField(
        verbose_name="Tavsif"
    )

    complaint_type = models.CharField(
        max_length=50,
        choices=TYPES,
        default="general",
        verbose_name="Shikoyat turi"
    )

    status = models.CharField(
        max_length=50,
        choices=STATUS,
        default="pending",
        verbose_name="Holat"
    )

    priority = models.CharField(
        max_length=50,
        choices=PRIORITY,
        default="medium",
        verbose_name="Muhimlik darajasi"
    )

    # Admin response
    resolution_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Yechim eslatmalari"
    )

    resolved_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_user_complaints",
        verbose_name="Hal qilgan"
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Hal qilingan vaqt"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan"
    )

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.subject}"

    def save(self, *args, **kwargs):
        # Auto-set priority based on complaint type
        if self.complaint_type == "fake_credentials":
            self.priority = "urgent"
        elif self.complaint_type in ["unprofessional_behavior", "pricing_issue"]:
            self.priority = "high"
        elif self.complaint_type == "wrong_information":
            self.priority = "medium"
        else:  # other
            self.priority = "low"

        # Set resolved_at when status changes to resolved
        if self.status == "resolved" and not self.resolved_at:
            from django.utils import timezone
            self.resolved_at = timezone.now()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "User Complaint"
        verbose_name_plural = "User Complaints"
        db_table = "user_complaint"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["complaint_type"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["created_at"]),
        ]


class UserComplaintFile(models.Model):
    """Files attached to user complaints"""

    complaint = models.ForeignKey(
        UserComplaint,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Shikoyat"
    )

    file = models.FileField(
        upload_to="user_complaint_files/%Y/%m/%d/",
        verbose_name="Fayl"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yuklangan vaqt"
    )

    def __str__(self):
        return f"File for {self.complaint.subject}"

    class Meta:
        verbose_name = "User Complaint File"
        verbose_name_plural = "User Complaint Files"
        db_table = "user_complaint_file"
        ordering = ["-uploaded_at"]
