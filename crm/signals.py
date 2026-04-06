from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Actividad

@receiver(pre_save, sender=Actividad)
def registrar_fecha_completada(sender, instance, **kwargs):
    if instance.status == 'COMPLETADA' and not instance.fecha_completada:
        instance.fecha_completada = timezone.now()
    elif instance.status != 'COMPLETADA':
        instance.fecha_completada = None
