# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

# Campos que solo deben cambiar mediante los botones del flujo
PROTECTED_FIELDS = {'state', 'hora_llegada', 'hora_salida'}

# Campos que solo puede escribir un supervisor
SUPERVISOR_ONLY_FIELDS = {'observacion_supervisor'}

# Estados en los que el técnico puede editar el reporte
TECNICO_EDITABLE_STATES = ('borrador', 'programado', 'en_proceso', 'rechazado')


class SecurityReport(models.Model):
    _name = 'security.report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
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
        tracking=True,
    )

    # ==========================================
    # CLIENTE Y UBICACIÓN
    # ==========================================

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
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
        tracking=True,
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
        tracking=True,
    )

    # ==========================================
    # DESCRIPCIÓN DEL TRABAJO
    # ==========================================

    descripcion = fields.Text(
        string='Descripción del Trabajo',
    )

    line_ids = fields.One2many(
        'security.report.line',
        'report_id',
        string='Equipos y Materiales',
        copy=True,
    )

    equipos = fields.Text(
        string='Otros Materiales / Detalle',
        help='Detalle adicional que no esté en las líneas de equipos '
             '(cableado, conectores, etc.).',
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
            ('rechazado', 'Rechazado'),
        ],
        string='Estado',
        default='borrador',
        required=True,
        copy=False,
        tracking=True,
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
        copy=False,
    )

    nombre_receptor = fields.Char(
        string='Nombre de quien recibe',
        help='Nombre completo de la persona que firma el reporte.',
    )

    # ==========================================
    # CONTROL DE TIEMPOS Y ANÁLISIS
    # ==========================================

    duracion_estimada = fields.Float(
        string='Duración Estimada (Horas)',
        default=2.0,
        help='Tiempo previsto para el trabajo. Se usa para dibujar el bloque en la agenda.',
    )

    hora_llegada = fields.Datetime(
        string='Hora de Llegada',
        readonly=True,
        copy=False,
    )

    hora_salida = fields.Datetime(
        string='Hora de Salida',
        readonly=True,
        copy=False,
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
        tracking=True,
    )

    # ==========================================
    # SEGURIDAD
    # ==========================================

    def _is_supervisor(self):
        user = self.env.user
        return (
            self.env.su
            or user.has_group('security_reports.group_security_supervisor')
            or user.has_group('base.group_system')
        )

    es_supervisor = fields.Boolean(compute='_compute_permisos')
    es_editable = fields.Boolean(compute='_compute_permisos')

    @api.depends('state')
    def _compute_permisos(self):
        """Banderas para la vista: qué puede hacer el usuario actual."""
        supervisor = self._is_supervisor()
        for rec in self:
            rec.es_supervisor = supervisor
            if supervisor:
                rec.es_editable = rec.state != 'validado'
            else:
                rec.es_editable = rec.state in TECNICO_EDITABLE_STATES

    def _check_supervisor(self):
        if not self._is_supervisor():
            raise AccessError(
                _('Solo un supervisor de operaciones puede realizar esta acción.')
            )

    def _check_state(self, allowed):
        labels = dict(self._fields['state'].selection)
        for rec in self:
            if rec.state not in allowed:
                raise UserError(_(
                    'El reporte %(name)s está en estado "%(state)s" y no admite esta acción.',
                    name=rec.name,
                    state=labels[rec.state],
                ))

    def _set_state(self, state, **vals):
        """Único punto por el que se cambia el estado (y los tiempos)."""
        vals['state'] = state
        self.with_context(security_report_action=True).write(vals)

    def write(self, vals):
        if (
            not self.env.context.get('security_report_action')
            and not self._is_supervisor()
        ):
            if PROTECTED_FIELDS & set(vals):
                raise AccessError(_(
                    'El estado y los tiempos solo se modifican con los botones del reporte.'
                ))
            if SUPERVISOR_ONLY_FIELDS & set(vals):
                raise AccessError(_(
                    'Solo un supervisor puede escribir la observación del supervisor.'
                ))
            if 'tecnico_id' in vals and any(
                rec.tecnico_id.id != vals['tecnico_id'] for rec in self
            ):
                raise AccessError(_('Solo un supervisor puede reasignar el técnico.'))
            if any(rec.state not in TECNICO_EDITABLE_STATES for rec in self):
                raise UserError(_(
                    'El reporte está pendiente de validación o validado y ya no se puede modificar.'
                ))
        return super().write(vals)

    # ==========================================
    # NOTIFICACIONES Y ACTIVIDADES
    # ==========================================

    def _notify_supervisors(self):
        """Avisa a los supervisores que hay un reporte por validar."""
        self.ensure_one()
        group = self.env.ref('security_reports.group_security_supervisor')
        supervisors = group.sudo().users.filtered(
            lambda u: u.active and u != self.env.user
        )
        for sup in supervisors:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=sup.id,
                summary=_('Validar reporte %s', self.name),
            )
        self.message_post(
            body=_('Reporte finalizado por %s. Pendiente de validación.', self.env.user.name),
            partner_ids=supervisors.partner_id.ids,
            subtype_xmlid='mail.mt_comment',
        )

    def _notify_tecnico(self, body, with_activity=False):
        """Avisa al técnico asignado del resultado de la revisión."""
        self.ensure_one()
        tecnico = self.tecnico_id
        if not tecnico:
            return
        if with_activity and tecnico != self.env.user:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=tecnico.id,
                summary=_('Corregir reporte %s', self.name),
                note=self.observacion_supervisor or '',
            )
        self.message_post(
            body=body,
            partner_ids=tecnico.partner_id.ids,
            subtype_xmlid='mail.mt_comment',
        )

    def _clear_pending_activities(self):
        self.sudo().activity_unlink(['mail.mail_activity_data_todo'])

    # ==========================================
    # MÉTODOS DE CAMBIO DE ESTADO
    # ==========================================

    def action_programar(self):
        self._check_state(['borrador'])
        self._set_state('programado')

    def action_iniciar_trabajo(self):
        self._check_state(['programado'])
        # Captura la hora exacta del servidor
        self._set_state(
            'en_proceso',
            hora_llegada=fields.Datetime.now(),
            hora_salida=False,
        )

    def action_finalizar(self):
        self._check_state(['en_proceso'])
        for rec in self:
            if not rec.descripcion:
                raise UserError(_('Debe describir el trabajo antes de finalizarlo.'))
            if not rec.image_ids:
                raise UserError(_('Debe subir al menos una foto de evidencia antes de finalizar.'))
            if not rec.firma_cliente:
                raise UserError(_('Falta la firma: el cliente debe firmar antes de cerrar el reporte.'))
            rec._set_state('finalizado', hora_salida=fields.Datetime.now())
            rec._clear_pending_activities()
            rec._notify_supervisors()

    def action_validar(self):
        self._check_supervisor()
        self._check_state(['finalizado'])
        for rec in self:
            rec._set_state('validado')
            rec._clear_pending_activities()
            rec._notify_tecnico(_('Su reporte %s fue validado.', rec.name))

    def action_rechazar(self):
        self._check_supervisor()
        self._check_state(['finalizado'])
        for rec in self:
            if not rec.observacion_supervisor:
                raise UserError(_(
                    'Escriba la observación del supervisor (pestaña "Revisión del Jefe") '
                    'antes de rechazar el reporte %s.', rec.name
                ))
            rec._set_state('rechazado')
            rec._clear_pending_activities()
            rec._notify_tecnico(
                _('Su reporte %(name)s fue rechazado: %(obs)s',
                  name=rec.name, obs=rec.observacion_supervisor),
                with_activity=True,
            )

    def action_reabrir(self):
        """El técnico retoma un reporte rechazado para corregirlo."""
        self._check_state(['rechazado'])
        self._set_state('en_proceso', hora_salida=False)
        self._clear_pending_activities()

    def action_borrador(self):
        self._check_supervisor()
        self._check_state(['programado', 'rechazado'])
        self._set_state('borrador')

    # ==========================================
    # GENERACIÓN AUTOMÁTICA DEL NÚMERO
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not self._is_supervisor():
                # Un técnico solo crea reportes propios y en borrador
                for field_name in PROTECTED_FIELDS | SUPERVISOR_ONLY_FIELDS:
                    vals.pop(field_name, None)
                vals['tecnico_id'] = self.env.user.id
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'security.report'
                ) or 'Nuevo'
        return super().create(vals_list)
