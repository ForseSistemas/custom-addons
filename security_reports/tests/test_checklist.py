# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestChecklistYGps(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tecnico = new_test_user(
            cls.env, login='tecnico_check',
            groups='base.group_user,security_reports.group_security_tecnico',
        )
        cls.supervisor = new_test_user(
            cls.env, login='supervisor_check',
            groups='base.group_user,security_reports.group_security_supervisor',
        )
        cls.cliente = cls.env['res.partner'].create({'name': 'Cliente checklist'})
        cls.Report = cls.env['security.report']

    def _crear(self, **vals):
        vals.setdefault('partner_id', self.cliente.id)
        vals.setdefault('tecnico_id', self.tecnico.id)
        return self.Report.create(vals)

    def _listo_para_finalizar(self):
        return self._crear(
            state='en_proceso',
            descripcion='Trabajo realizado',
            firma_cliente=base64.b64encode(b'firma'),
            image_ids=[(0, 0, {'name': 'foto.png', 'raw': b'foto'})],
        )

    # ---------- Generación desde la plantilla ----------

    def test_el_reporte_recibe_el_checklist_de_su_tipo(self):
        plantilla = self.env.ref('security_reports.checklist_template_instalacion')
        reporte = self._crear(tipo_trabajo='instalacion')
        self.assertEqual(
            reporte.check_ids.mapped('name'), plantilla.line_ids.mapped('name')
        )
        self.assertFalse(any(reporte.check_ids.mapped('hecho')))

    def test_cambiar_el_tipo_rehace_el_checklist_si_no_hay_nada_marcado(self):
        reporte = self._crear(tipo_trabajo='instalacion')
        reporte.tipo_trabajo = 'mantenimiento'
        plantilla = self.env.ref('security_reports.checklist_template_mantenimiento')
        self.assertEqual(
            reporte.check_ids.mapped('name'), plantilla.line_ids.mapped('name')
        )

    def test_cambiar_el_tipo_conserva_lo_marcado(self):
        reporte = self._crear(tipo_trabajo='instalacion')
        reporte.check_ids[0].hecho = True
        nombres = reporte.check_ids.mapped('name')
        reporte.tipo_trabajo = 'mantenimiento'
        self.assertEqual(reporte.check_ids.mapped('name'), nombres)

    # ---------- Obligatorios al finalizar ----------

    def test_no_se_finaliza_con_puntos_obligatorios_pendientes(self):
        reporte = self._listo_para_finalizar()
        with self.assertRaises(UserError):
            reporte.with_user(self.tecnico).action_finalizar()
        self.assertEqual(reporte.state, 'en_proceso')

    def test_se_finaliza_al_marcar_los_obligatorios(self):
        reporte = self._listo_para_finalizar()
        reporte.check_ids.filtered('obligatorio').write({'hecho': True})
        reporte.with_user(self.tecnico).action_finalizar()
        self.assertEqual(reporte.state, 'finalizado')

    def test_avance_del_checklist(self):
        reporte = self._crear(tipo_trabajo='diagnostico')
        total = len(reporte.check_ids)
        reporte.check_ids[0].hecho = True
        self.assertEqual(reporte.check_total, total)
        self.assertEqual(reporte.check_hechos, 1)
        self.assertAlmostEqual(reporte.checklist_progress, 100.0 / total)

    # ---------- Permisos ----------

    def test_tecnico_marca_pero_no_edita_los_puntos(self):
        reporte = self._crear(state='en_proceso')
        punto = reporte.check_ids[0].with_user(self.tecnico)
        punto.write({'hecho': True})
        self.assertTrue(punto.hecho)
        with self.assertRaises(AccessError):
            punto.write({'name': 'otro texto'})
        with self.assertRaises(AccessError):
            punto.write({'obligatorio': False})

    def test_tecnico_no_crea_ni_borra_puntos(self):
        reporte = self._crear(state='en_proceso')
        with self.assertRaises(AccessError):
            self.env['security.report.check'].with_user(self.tecnico).create({
                'report_id': reporte.id, 'name': 'Punto inventado',
            })
        with self.assertRaises(AccessError):
            reporte.check_ids[0].with_user(self.tecnico).unlink()

    def test_tecnico_no_marca_puntos_de_un_reporte_finalizado(self):
        reporte = self._crear(state='finalizado')
        with self.assertRaises(UserError):
            reporte.check_ids[0].with_user(self.tecnico).write({'hecho': True})

    def test_tecnico_no_ve_ni_edita_las_plantillas(self):
        Plantilla = self.env['security.checklist.template']
        with self.assertRaises(AccessError):
            Plantilla.with_user(self.tecnico).search([])
        with self.assertRaises(AccessError):
            Plantilla.with_user(self.tecnico).create({
                'name': 'Mía', 'tipo_trabajo': 'instalacion',
            })

    def test_supervisor_administra_las_plantillas(self):
        plantilla = self.env['security.checklist.template'].with_user(
            self.supervisor
        ).create({
            'name': 'Plantilla nueva',
            'tipo_trabajo': 'reparacion',
            'line_ids': [(0, 0, {'name': 'Punto 1'})],
        })
        self.assertEqual(len(plantilla.line_ids), 1)

    # ---------- GPS ----------

    def test_enlace_al_mapa_con_la_ubicacion(self):
        reporte = self._crear()
        self.assertFalse(reporte.gps_inicio_url)
        reporte.write({'gps_inicio_lat': -2.1894, 'gps_inicio_lng': -79.8891})
        self.assertIn('-2.1894', reporte.gps_inicio_url)
        self.assertIn('-79.8891', reporte.gps_inicio_url)
        self.assertFalse(reporte.gps_fin_url)

    def test_tecnico_guarda_su_ubicacion_al_iniciar(self):
        reporte = self._crear(state='programado')
        como_tecnico = reporte.with_user(self.tecnico)
        como_tecnico.write({'gps_inicio_lat': -2.19, 'gps_inicio_lng': -79.88})
        como_tecnico.action_iniciar_trabajo()
        self.assertEqual(reporte.state, 'en_proceso')
        self.assertAlmostEqual(reporte.gps_inicio_lat, -2.19)
