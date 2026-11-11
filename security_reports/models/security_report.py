# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SecurityReport(models.Model):
    _name = 'security.report'
    _description = 'Reporte Técnico de Seguridad'
    _order = 'fecha desc, id desc'

    # ==========================================
    # CAMPOS BÁSICOS
    # ==========================================

    name = fields.Char(
        string='Número de Reporte',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
    )

    fecha = fields.Datetime(
        string='Fecha del Trabajo',
        required=True,
        default=fields.Datetime.now,
    )

    # ==========================================
    # CLIENTE Y UBICACIÓN
    # ==========================================

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
    )

    direccion = fields.Char(
        string='Dirección del Trabajo',
    )

    # ==========================================
    # TÉCNICO ASIGNADO
    # ==========================================

    tecnico_id = fields.Many2one(
        'res.users',
        string='Técnico Asignado',
        default=lambda self: self.env.user,
    )

    # ==========================================
    # TIPO DE TRABAJO
    # ==========================================

    tipo_trabajo = fields.Selection(
        selection=[
            ('instalacion', 'Instalación'),
            ('mantenimiento', 'Mantenimiento'),
            ('reparacion', 'Reparación'),
            ('diagnostico', 'Diagnóstico'),
            ('desinstalacion', 'Desinstalación'),
        ],
        string='Tipo de Trabajo',
        required=True,
        default='instalacion',
    )

    # ==========================================
    # DESCRIPCIÓN DEL TRABAJO
    # ==========================================

    descripcion = fields.Text(
        string='Descripción del Trabajo',
    )

    equipos = fields.Text(
        string='Equipos / Materiales Utilizados',
        help='Detalle de cámaras, DVR, cableado y otros equipos usados',
    )

    # ==========================================
    # ESTADO DEL REPORTE
    # ==========================================

    state = fields.Selection(
        selection=[
            ('borrador', 'Borrador'),
            ('programado', 'Programado'),
            ('en_proceso', 'En Proceso'),
            ('finalizado', 'Finalizado'),
            ('validado', 'Validado'),
        ],
        string='Estado',
        default='borrador',
        required=True,
    )

    # ==========================================
    # NOTAS INTERNAS
    # ==========================================

    notas = fields.Text(
        string='Notas Internas',
    )

    # ==========================================
    # EVIDENCIA: FOTOS Y FIRMA
    # ==========================================

    image_ids = fields.Many2many(
        'ir.attachment',
        'security_report_ir_attachment_rel',
        'report_id',
        'attachment_id',
        string='Fotos del Trabajo',
        help='Suba imágenes del antes, durante y después del trabajo.',
    )

    firma_cliente = fields.Binary(
        string='Firma del Cliente',
        help='Firma de la persona que recibe el trabajo.',
    )

    nombre_receptor = fields.Char(
        string='Nombre de quien recibe',
        help='Nombre completo de la persona que firma el reporte.',
    )

    # ==========================================
    # CONTROL DE TIEMPOS Y ANÁLISIS
    # ==========================================

    hora_llegada = fields.Datetime(
        string='Hora de Llegada', 
        readonly=True,
    )

    hora_salida = fields.Datetime(
        string='Hora de Salida', 
        readonly=True,
    )

    duracion_horas = fields.Float(
        string='Duración (Horas)', 
        compute='_compute_duracion', 
        store=True,
    )

    @api.depends('hora_llegada', 'hora_salida')
    def _compute_duracion(self):
        for rec in self:
            if rec.hora_llegada and rec.hora_salida:
                # Restamos las fechas y lo pasamos a horas
                delta = rec.hora_salida - rec.hora_llegada
                rec.duracion_horas = delta.total_seconds() / 3600.0
            else:
                rec.duracion_horas = 0.0

    # ==========================================
    # OBSERVACIONES DEL SUPERVISOR
    # ==========================================

    observacion_supervisor = fields.Text(
        string='Observación del Supervisor',
        help='Comentarios del jefe al validar o rechazar el trabajo.',
    )

    # ==========================================
    # MÉTODOS DE CAMBIO DE ESTADO
    # ==========================================

    def action_programar(self):
        for rec in self:
            rec.state = 'programado'

    def action_iniciar_trabajo(self):
        for rec in self:
            # Captura la hora exacta del servidor
            rec.hora_llegada = fields.Datetime.now()
            rec.state = 'en_proceso'

    def action_finalizar(self):
        for rec in self:
            # 1. Validar descripción
            if not rec.descripcion:
                raise UserError('Debe describir el trabajo antes de finalizarlo.')
            
            # 2. Validar fotos
            if not rec.image_ids:
                raise UserError('¡Alto ahí! Debe subir al menos una foto de evidencia antes de finalizar.')
            
            # 3. Validar firma
            if not rec.firma_cliente:
                raise UserError('¡Falta la firma! El cliente debe firmar en la pantalla antes de cerrar el reporte.')
            
            # 4. Todo en orden: capturamos hora de salida y cerramos
            rec.hora_salida = fields.Datetime.now()
            rec.state = 'finalizado'

    def action_validar(self):
        for rec in self:
            rec.state = 'validado'

    def action_borrador(self):
        for rec in self:
            rec.state = 'borrador'

    # ==========================================
    # GENERACIÓN AUTOMÁTICA DEL NÚMERO
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'security.report'
                ) or 'Nuevo'
        return super().create(vals_list)