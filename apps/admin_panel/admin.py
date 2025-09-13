from django.contrib import admin
from .models import DoctorComplaint, DoctorComplaintFile


class DoctorComplaintFileInline(admin.TabularInline):
    model = DoctorComplaintFile
    extra = 1
    readonly_fields = ('uploaded_at',)


@admin.register(DoctorComplaint)
class DoctorComplaintAdmin(admin.ModelAdmin):
    list_display = ('subject', 'doctor', 'complaint_type', 'status', 'priority', 'created_at', )
    list_filter = ('complaint_type', 'status', 'priority', 'created_at')
    search_fields = ('subject', 'doctor__user__first_name', 'doctor__user__last_name', 'doctor__user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DoctorComplaintFileInline]
    
    fieldsets = (
        (None, {
            'fields': ('doctor', 'subject', 'description', 'resolution_notes')
        }),
        ('Classification', {
            'fields': ('complaint_type', 'status', 'priority')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DoctorComplaintFile)
class DoctorComplaintFileAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'file', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('complaint__subject',)
    readonly_fields = ('uploaded_at',)