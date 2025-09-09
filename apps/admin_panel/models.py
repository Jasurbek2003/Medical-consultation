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

