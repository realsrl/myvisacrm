from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Actividad






import json
import logging
from pathlib import Path
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from .models import Agencia, TipoCaso, SubTipoCaso, CategoriaDocumento, CaseStatus, Actividad
from formularios.models import Formulario, Seccion, FormularioSeccion, Pregunta

logger = logging.getLogger(__name__)



@receiver(pre_save, sender=Actividad)
def registrar_fecha_completada(sender, instance, **kwargs):
    if instance.status == 'COMPLETADA' and not instance.fecha_completada:
        instance.fecha_completada = timezone.now()
    elif instance.status != 'COMPLETADA':
        instance.fecha_completada = None


# ==========================================
# SEÑAL 2: Agencia (Creación de recursos por defecto)
# ==========================================
@receiver(post_save, sender=Agencia)
def configurar_defaults_agencia(sender, instance, created, **kwargs):
    """Crea tipos, categorías, estados y formularios por defecto al crear una Agencia."""
    if created:
        _crear_recursos_por_defecto(instance)

@transaction.atomic
def _crear_recursos_por_defecto(agencia):
    # 1. ESTADOS DEL EMBUDO (CaseStatus)
    estados_default = [
        ("Evaluación Inicial", 1, "#6c757d"),
        ("Recolección de Documentos", 2, "#0d6efd"),
        ("Firma y Pago", 3, "#6610f2"),
        ("Pendiente Aprobación USCIS", 4, "#ffc107"),
        ("Aprobado / Entrevista", 5, "#198754"),
    ]
    for nombre, orden, color in estados_default:
        CaseStatus.objects.get_or_create(agencia=agencia, nombre=nombre, defaults={"orden": orden, "color": color})

    # 2. TIPOS Y SUBTIPOS DE CASOS
    tipos_data = [
        ("Inmigrante", ["Proceso Consular", "Ajuste de Estatus"]),
        ("No Inmigrante", ["Visa Turista/Negocios", "Visa de Trabajo"]),
        ("Humanitario", ["Asilo/Refugio", "TPS"]),
    ]
    for tipo_nombre, subtipos in tipos_data:
        tipo, _ = TipoCaso.objects.get_or_create(agencia=agencia, nombre=tipo_nombre)
        for st_nombre in subtipos:
            SubTipoCaso.objects.get_or_create(tipo_caso=tipo, nombre=st_nombre)

    # 3. CATEGORÍAS DE DOCUMENTOS
    categorias_default = [
        "Identificación Oficial", "Comprobantes Financieros", 
        "Antecedentes/Penales", "Documentos de Caso Migratorio", "Subido por Cliente"
    ]
    for cat_nombre in categorias_default:
        CategoriaDocumento.objects.get_or_create(agencia=agencia, nombre=cat_nombre)

    # 4. FORMULARIOS DESDE ARCHIVOS JSON
    forms_dir = Path(__file__).resolve().parent / "fixtures" / "default_forms"
    if forms_dir.exists():
        for json_file in forms_dir.glob("*.json"):
            try:
                _cargar_formulario_desde_json(agencia, json_file)
            except Exception as e:
                logger.error(f"Error cargando {json_file.name} para agencia {agencia.nombre}: {e}")

def _cargar_formulario_desde_json(agencia, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    formulario, _ = Formulario.objects.get_or_create(
        agencia=agencia,
        nombre=data["nombre"],
        defaults={
            "descripcion": data.get("descripcion", ""),
            "activo": data.get("activo", True)
        }
    )

    for idx, sec_data in enumerate(data.get("secciones", [])):
        seccion, _ = Seccion.objects.get_or_create(
            agencia=agencia,
            nombre=sec_data["nombre"],
            defaults={
                "descripcion": sec_data.get("descripcion", ""),
                "repetible": sec_data.get("repetible", False),
                "activo": sec_data.get("activo", True)
            }
        )

        FormularioSeccion.objects.get_or_create(
            formulario=formulario,
            seccion=seccion,
            defaults={"orden": idx}
        )

        for q_data in sec_data.get("preguntas", []):
            Pregunta.objects.get_or_create(
                seccion=seccion,
                texto_pregunta=q_data["texto"],
                defaults={
                    "tipo_dato": q_data.get("tipo", "TEXTO"),
                    "es_requerida": q_data.get("requerida", True),
                    "orden": q_data.get("orden", 0),
                    "opciones": q_data.get("opciones", ""),
                    "ayuda_visual": q_data.get("ayuda_visual", "")
                }
            )