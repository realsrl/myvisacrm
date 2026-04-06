from django import forms
from .models import Documento, MensajeCliente, ActualizacionCliente, Caso, CaseStatus, Credencial
from django.contrib.auth.models import User

class DocumentoClienteForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ['nombre_documento', 'detalle', 'archivo']
        labels = {
            'nombre_documento': 'Título del Documento',
            'detalle': 'Mensaje o Detalle (Opcional)',
            'archivo': 'Seleccionar Archivo',
        }
        widgets = {
            'nombre_documento': forms.TextInput(attrs={'placeholder': 'Ej: Acta de nacimiento, Pasaporte...'}),
            'detalle': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Explica brevemente de qué trata este documento...'
            }),
        }

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
    tipo = forms.ChoiceField(
        choices=Caso.TIPO_CHOICES,
        label='Tipo de Visa',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sub_tipo = forms.ChoiceField(
        choices=Caso.SUB_TIPO_CHOICES,
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

