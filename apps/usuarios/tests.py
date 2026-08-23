from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import Usuario, SolicitudProfesor


class FlujoRegistroYAccesoProfesorTests(TestCase):
    """
    Pruebas unitarias y de integracion para el flujo de aprobacion de profesores,
    restriccion de roles y periodo de bloqueo (cooldown) de 2 horas tras un rechazo.
    """

    def setUp(self):
        self.client = APIClient()
        self.url_registro = reverse('usuarios:registro')
        self.url_login = reverse('usuarios:login')

    def test_registro_estudiante_se_crea_activo_y_puede_iniciar_sesion(self):
        """Un estudiante registrado se activa de inmediato y puede loguearse."""
        datos = {
            'email': 'estudiante@test.com',
            'username': 'estudiante1',
            'first_name': 'Juan',
            'last_name': 'Perez',
            'rol': Usuario.Rol.ESTUDIANTE,
            'password': 'Password123!',
            'password_confirmacion': 'Password123!',
        }
        res_registro = self.client.post(self.url_registro, datos, format='json')
        self.assertEqual(res_registro.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_registro.data['usuario']['activo'])

        usuario = Usuario.objects.get(email='estudiante@test.com')
        self.assertTrue(usuario.is_active)
        self.assertEqual(usuario.rol, Usuario.Rol.ESTUDIANTE)

        # Login inmediato exitoso
        res_login = self.client.post(self.url_login, {
            'email': 'estudiante@test.com',
            'password': 'Password123!',
        }, format='json')
        self.assertEqual(res_login.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_login.data)

    def test_registro_profesor_crea_cuenta_inactiva_y_solicitud_pendiente(self):
        """Un profesor registrado se crea inactivo y genera SolicitudProfesor pendiente."""
        datos = {
            'email': 'profesor@test.com',
            'username': 'profesor1',
            'first_name': 'Maria',
            'last_name': 'Gomez',
            'rol': Usuario.Rol.PROFESOR,
            'password': 'Password123!',
            'password_confirmacion': 'Password123!',
        }
        res_registro = self.client.post(self.url_registro, datos, format='json')
        self.assertEqual(res_registro.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res_registro.data['usuario']['activo'])

        usuario = Usuario.objects.get(email='profesor@test.com')
        self.assertFalse(usuario.is_active)
        self.assertEqual(usuario.rol, Usuario.Rol.PROFESOR)

        # Comprobar que existe la solicitud pendiente
        self.assertTrue(hasattr(usuario, 'solicitud_profesor'))
        self.assertEqual(usuario.solicitud_profesor.estado, SolicitudProfesor.Estado.PENDIENTE)

    def test_login_profesor_pendiente_es_bloqueado(self):
        """Un profesor con solicitud pendiente no puede iniciar sesion."""
        datos = {
            'email': 'profesor_pendiente@test.com',
            'username': 'profesor_pend',
            'first_name': 'Carlos',
            'last_name': 'Lopez',
            'rol': Usuario.Rol.PROFESOR,
            'password': 'Password123!',
            'password_confirmacion': 'Password123!',
        }
        self.client.post(self.url_registro, datos, format='json')

        res_login = self.client.post(self.url_login, {
            'email': 'profesor_pendiente@test.com',
            'password': 'Password123!',
        }, format='json')
        self.assertEqual(res_login.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pendiente de aprobacion', str(res_login.data))

    def test_aprobacion_de_solicitud_permite_login(self):
        """Al aceptar la solicitud, la cuenta se activa y el login funciona."""
        datos = {
            'email': 'profesor_aprobado@test.com',
            'username': 'profesor_apr',
            'first_name': 'Ana',
            'last_name': 'Martinez',
            'rol': Usuario.Rol.PROFESOR,
            'password': 'Password123!',
            'password_confirmacion': 'Password123!',
        }
        self.client.post(self.url_registro, datos, format='json')
        usuario = Usuario.objects.get(email='profesor_aprobado@test.com')
        
        # Aceptar solicitud
        usuario.solicitud_profesor.aceptar()
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_active)
        self.assertEqual(usuario.solicitud_profesor.estado, SolicitudProfesor.Estado.ACEPTADA)

        # Login exitoso
        res_login = self.client.post(self.url_login, {
            'email': 'profesor_aprobado@test.com',
            'password': 'Password123!',
        }, format='json')
        self.assertEqual(res_login.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_login.data)

    def test_rechazo_de_solicitud_bloquea_registro_por_2_horas(self):
        """Al rechazar la solicitud, el correo queda bloqueado para registro durante 2 horas."""
        datos = {
            'email': 'profesor_rechazado@test.com',
            'username': 'profesor_rech',
            'first_name': 'Pedro',
            'last_name': 'Diaz',
            'rol': Usuario.Rol.PROFESOR,
            'password': 'Password123!',
            'password_confirmacion': 'Password123!',
        }
        self.client.post(self.url_registro, datos, format='json')
        usuario = Usuario.objects.get(email='profesor_rechazado@test.com')

        # Rechazar solicitud
        usuario.solicitud_profesor.rechazar(motivo='Perfil no cumple requisitos.')
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)
        self.assertEqual(usuario.solicitud_profesor.estado, SolicitudProfesor.Estado.RECHAZADA)

        # Intento de login bloqueado
        res_login = self.client.post(self.url_login, {
            'email': 'profesor_rechazado@test.com',
            'password': 'Password123!',
        }, format='json')
        self.assertEqual(res_login.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rechazada', str(res_login.data))

        # Intento de re-registro inmediato bloqueado por cooldown
        res_reregistro = self.client.post(self.url_registro, datos, format='json')
        self.assertEqual(res_reregistro.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Debes esperar 2 horas', str(res_reregistro.data))

    def test_re_registro_permitido_despues_de_2_horas(self):
        """Tras expirar las 2 horas de cooldown desde el rechazo, se permite volver a registrarse."""
        datos = {
            'email': 'profesor_expirado@test.com',
            'username': 'profesor_exp',
            'first_name': 'Laura',
            'last_name': 'Sanchez',
            'rol': Usuario.Rol.PROFESOR,
            'password': 'Password123!',
            'password_confirmacion': 'Password123!',
        }
        self.client.post(self.url_registro, datos, format='json')
        usuario = Usuario.objects.get(email='profesor_expirado@test.com')
        solicitud = usuario.solicitud_profesor

        # Simular rechazo ocurrido hace 2 horas y 1 minuto
        solicitud.estado = SolicitudProfesor.Estado.RECHAZADA
        solicitud.fecha_resolucion = timezone.now() - timedelta(hours=2, minutes=1)
        solicitud.save()

        self.assertFalse(solicitud.esta_en_cooldown())

        # Re-registro permitido
        res_reregistro = self.client.post(self.url_registro, datos, format='json')
        self.assertEqual(res_reregistro.status_code, status.HTTP_201_CREATED)

    def test_registro_rechaza_rol_administrador(self):
        """No se permite registrar un usuario con rol de Administrador."""
        datos = {
            'email': 'admin_falso@test.com',
            'username': 'admin_falso',
            'first_name': 'Hacker',
            'last_name': 'Test',
            'rol': Usuario.Rol.ADMINISTRADOR,
            'password': 'Password123!',
            'password_confirmacion': 'Password123!',
        }
        res = self.client.post(self.url_registro, datos, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
