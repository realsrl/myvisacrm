from django import forms
from .models import (
    Documento, MensajeCliente, ActualizacionCliente, Caso, CaseStatus, Credencial,
    Agencia, Checklist, ChecklistItem, ConfiguracionMensajes, TipoCaso, SubTipoCaso,
    PlantillaInstruccion
)

class PlantillaInstruccionForm(forms.ModelForm):
    class Meta:
        model = PlantillaInstruccion
        fields = ['nombre', 'contenido']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Requisitos de Pasaporte'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': '1. Llevar pasaporte vigente...'}),
        }
from django.contrib.auth.models import User

class DocumentoClienteForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ['nombre_documento', 'categoria', 'detalle', 'archivo']
        labels = {
            'nombre_documento': 'Título del Documento',
            'categoria': 'Categoría',
            'detalle': 'Mensaje o Detalle (Opcional)',
            'archivo': 'Seleccionar Archivo',
        }
        widgets = {
            'nombre_documento': forms.TextInput(attrs={'placeholder': 'Ej: Acta de nacimiento, Pasaporte...'}),
            'detalle': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Explica brevemente de qué trata este documento...'
            }),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, agency=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import CategoriaDocumento
        if agency:
            self.fields['categoria'].queryset = CategoriaDocumento.objects.filter(agencia=agency)
        else:
            self.fields['categoria'].queryset = CategoriaDocumento.objects.all()

class MensajeClienteForm(forms.ModelForm):
    class Meta:
        model = MensajeCliente
        fields = ['contenido']
        labels = {'contenido': ''}
        widgets = {
            'contenido': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Escribe tu mensaje al preparador...',
                'class': 'form-control',
            }),
        }

class ActualizacionForm(forms.ModelForm):
    class Meta:
        model = ActualizacionCliente
        fields = ['mensaje']
        labels = {'mensaje': ''}
        widgets = {
            'mensaje': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Escribe la actualización que verá el cliente en su portal...',
                'class': 'form-control',
            }),
        }


class NuevoCasoForm(forms.Form):
    """Form for creating a new case from the dashboard."""
    titulo = forms.CharField(
        max_length=200,
        label='Nombre del Caso',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Juan Pérez - Residencia Permanente',
        })
    )
    tipo = forms.ModelChoiceField(
        queryset=TipoCaso.objects.none(),
        label='Tipo de Caso',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sub_tipo = forms.ModelChoiceField(
        queryset=SubTipoCaso.objects.none(),
        label='Sub-Tipo',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    preparador = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Asignar a Agente',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status_inicial = forms.ModelChoiceField(
        queryset=CaseStatus.objects.none(),
        label='Estado Inicial',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Client user creation
    nombre_cliente = forms.CharField(
        max_length=100,
        label='Nombre del Cliente',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre completo del beneficiario',
        })
    )
    email_cliente = forms.EmailField(
        label='Email del Cliente',
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com (opcional)',
        })
    )
    username_cliente = forms.CharField(
        max_length=150,
        label='Usuario de Acceso (Cliente)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: jperez01',
        })
    )
    password_cliente = forms.CharField(
        max_length=128,
        label='Contraseña de Acceso (Cliente)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña para el portal del cliente',
        })
    )

    def __init__(self, *args, agencia=None, **kwargs):
        super().__init__(*args, **kwargs)
        if agencia:
            from .models import UserProfile
            # Team members of this agency
            team_user_ids = UserProfile.objects.filter(
                agencia=agencia, tipo='MIEMBRO'
            ).values_list('user_id', flat=True)
            self.fields['preparador'].queryset = User.objects.filter(
                id__in=team_user_ids
            )
            # Case statuses for this agency
            self.fields['status_inicial'].queryset = CaseStatus.objects.filter(
                agencia=agencia
            ).order_by('orden')
            # Dynamic Types and Subtypes
            self.fields['tipo'].queryset = TipoCaso.objects.filter(agencia=agencia)
            self.fields['sub_tipo'].queryset = SubTipoCaso.objects.filter(tipo_caso__agencia=agencia)


class CasoEditarForm(forms.Form):
    """Form único y reutilizable para editar el caso (titulo, status, tipo, sub_tipo, preparador)."""
    titulo = forms.CharField(
        max_length=200,
        label='Titular',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    status_actual = forms.ModelChoiceField(
        queryset=CaseStatus.objects.none(),
        label='Status del Caso',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tipo = forms.ModelChoiceField(
        queryset=TipoCaso.objects.none(),
        label='Tipo de Visa',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sub_tipo = forms.ModelChoiceField(
        queryset=SubTipoCaso.objects.none(),
        label='Sub-Tipo',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    preparador = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Preparador Asignado',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, agencia=None, **kwargs):
        super().__init__(*args, **kwargs)
        if agencia:
            from .models import UserProfile
            team_user_ids = UserProfile.objects.filter(
                agencia=agencia, tipo='MIEMBRO'
            ).values_list('user_id', flat=True)
            self.fields['preparador'].queryset = User.objects.filter(id__in=team_user_ids)
            self.fields['status_actual'].queryset = CaseStatus.objects.filter(
                agencia=agencia
            ).order_by('orden')
            self.fields['tipo'].queryset = TipoCaso.objects.filter(agencia=agencia)
            self.fields['sub_tipo'].queryset = SubTipoCaso.objects.filter(tipo_caso__agencia=agencia)


class ChecklistForm(forms.ModelForm):
    class Meta:
        model = Checklist
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Plantilla (ej: Requisitos Residencia)'})
        }

class ChecklistItemForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = ['texto', 'orden']
        widgets = {
            'texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción del ítem'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control'})
        }

class CaseStatusForm(forms.ModelForm):
    class Meta:
        model = CaseStatus
        fields = ['nombre', 'orden', 'color']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'})
        }

class ConfigMensajesForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionMensajes
        fields = ['limite', 'periodo']
        widgets = {
            'limite': forms.NumberInput(attrs={'class': 'form-control'}),
            'periodo': forms.Select(attrs={'class': 'form-select'})
        }

class PreparadorForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False, help_text="Dejar en blanco para mantener actual")
    es_admin = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

class TipoCasoForm(forms.ModelForm):
    class Meta:
        model = TipoCaso
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'})
        }

class SubTipoCasoForm(forms.ModelForm):
    class Meta:
        model = SubTipoCaso
        fields = ['tipo_caso', 'nombre']
        widgets = {
            'tipo_caso': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, agencia=None, **kwargs):
        super().__init__(*args, **kwargs)
        if agencia:
            self.fields['tipo_caso'].queryset = TipoCaso.objects.filter(agencia=agencia)

class CategoriaDocumentoForm(forms.ModelForm):
    class Meta:
        from .models import CategoriaDocumento
        model = CategoriaDocumento
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Acta de Nacimiento, Pasaporte...'})
        }

class DerivadoForm(forms.ModelForm):
    class Meta:
        from .models import Derivado
        model = Derivado
        fields = ['nombre', 'apellido', 'telefono', 'email']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }
