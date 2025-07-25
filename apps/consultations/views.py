from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response


@action(detail=True, methods=['post'])
def start_consultation(self, request, pk=None):
    consultation = self.get_object()
    consultation.actual_start_time = timezone.now()
    consultation.status = 'in_progress'
    consultation.save()
    return Response({'status': 'started'})