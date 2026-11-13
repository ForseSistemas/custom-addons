# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestPermisosReportes(TransactionCase):
    """Qué puede ver y hacer cada perfil: técnico de campo vs supervisor."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tecnico = new_test_user(
            cls.env, login='tecnico_prueba',
            groups='base.group_user,security_reports.group_security_tecnico',
        )
        cls.otro_tecnico = new_test_user(
            cls.env, login='otro_tecnico_prueba',
            groups='base.group_user,security_reports.group_security_tecnico',
        )
        cls.supervisor = new_test_user(
            cls.env, login='supervisor_prueba',
            groups='base.group_user,security_reports.group_security_supervisor',
        )
        cls.cliente = cls.env['res.partner'].create({'name': 'Cliente de prueba'})
        cls.Report = cls.env['security.report']
        cls.Line = cls.env['security.report.line']

    def _crear(self, tecnico=None, **vals):
        """Crea un reporte como superusuario (para preparar escenarios)."""
        vals.setdefault('partner_id', self.cliente.id)
        vals['tecnico_id'] = (tecnico or self.tecnico).id
        return self.Report.create(vals)

    # ---------- Visibilidad ----------

    def test_tecnico_solo_ve_sus_reportes(self):
        mio = self._crear()
        ajeno = self._crear(tecnico=self.otro_tecnico)
        visibles = self.Report.with_user(self.tecnico).search(
            [('id', 'in', (mio | ajeno).ids)]
        )
        self.assertEqual(visibles, mio)

    def test_supervisor_ve_todos_los_reportes(self):
        mio = self._crear()
        ajeno = self._crear(tecnico=self.otro_tecnico)
        visibles = self.Report.with_user(self.supervisor).search(
            [('id', 'in', (mio | ajeno).ids)]
        )
        self.assertEqual(visibles, mio | ajeno)

    # ---------- Lo que el técnico NO puede hacer ----------

    def test_tecnico_no_valida_ni_rechaza(self):
        reporte = self._crear(state='finalizado', observacion_supervisor='x')
        with self.assertRaises(AccessError):
            reporte.with_user(self.tecnico).action_validar()
        with self.assertRaises(AccessError):
            reporte.with_user(self.tecnico).action_rechazar()
        self.assertEqual(reporte.state, 'finalizado')

    def test_tecnico_no_cambia_el_estado_a_mano(self):
        reporte = self._crear(state='en_proceso')
        with self.assertRaises(AccessError):
            reporte.with_user(self.tecnico).write({'state': 'validado'})

    def test_tecnico_no_escribe_la_observacion_del_supervisor(self):
        reporte = self._crear(state='en_proceso')
        with self.assertRaises(AccessError):
            reporte.with_user(self.tecnico).write({'observacion_supervisor': 'ok'})

    def test_tecnico_no_reasigna_el_reporte(self):
        reporte = self._crear(state='borrador')
        with self.assertRaises(AccessError):
            reporte.with_user(self.tecnico).write({'tecnico_id': self.otro_tecnico.id})

    def test_tecnico_solo_crea_reportes_propios(self):
        reporte = self.Report.with_user(self.tecnico).create({
            'partner_id': self.cliente.id,
            'tecnico_id': self.otro_tecnico.id,
            'state': 'validado',
        })
        self.assertEqual(reporte.tecnico_id, self.tecnico)
        self.assertEqual(reporte.state, 'borrador')

    def test_tecnico_no_borra_reportes(self):
        reporte = self._crear()
        with self.assertRaises(AccessError):
            reporte.with_user(self.tecnico).unlink()

    def test_tecnico_no_edita_un_reporte_pendiente_de_validacion(self):
        reporte = self._crear(state='finalizado')
        with self.assertRaises(UserError):
            reporte.with_user(self.tecnico).write({'descripcion': 'cambio tardío'})

    def test_tecnico_no_toca_equipos_de_un_reporte_finalizado(self):
        reporte = self._crear(state='finalizado')
        with self.assertRaises(UserError):
            self.Line.with_user(self.tecnico).create({
                'report_id': reporte.id, 'name': 'Cámara',
            })

    def test_tecnico_si_edita_equipos_mientras_trabaja(self):
        reporte = self._crear(state='en_proceso')
        linea = self.Line.with_user(self.tecnico).create({
            'report_id': reporte.id, 'name': 'Cámara', 'cantidad': 2,
        })
        self.assertEqual(linea.report_id, reporte)

    # ---------- Flujo completo con los dos perfiles ----------

    def test_flujo_tecnico_finaliza_y_supervisor_valida(self):
        reporte = self._crear(state='programado')
        como_tecnico = reporte.with_user(self.tecnico)
        como_tecnico.action_iniciar_trabajo()
        self.assertEqual(reporte.state, 'en_proceso')
        como_tecnico.write({
            'descripcion': 'Instalación de cámara',
            'firma_cliente': base64.b64encode(b'firma'),
            'image_ids': [(0, 0, {'name': 'foto.png', 'raw': b'foto'})],
        })
        como_tecnico.action_finalizar()
        self.assertEqual(reporte.state, 'finalizado')
        self.assertTrue(reporte.hora_salida)

        reporte.with_user(self.supervisor).action_validar()
        self.assertEqual(reporte.state, 'validado')

    def test_supervisor_debe_justificar_el_rechazo(self):
        reporte = self._crear(state='finalizado')
        como_supervisor = reporte.with_user(self.supervisor)
        with self.assertRaises(UserError):
            como_supervisor.action_rechazar()
        como_supervisor.write({'observacion_supervisor': 'Faltan fotos del después'})
        como_supervisor.action_rechazar()
        self.assertEqual(reporte.state, 'rechazado')
        # el técnico puede reabrirlo para corregir
        reporte.with_user(self.tecnico).action_reabrir()
        self.assertEqual(reporte.state, 'en_proceso')
