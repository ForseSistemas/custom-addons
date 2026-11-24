# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .security_report import TECNICO_EDITABLE_STATES, TIPO_TRABAJO_SELECTION


class SecurityChecklistTemplate(models.Model):
    """Plantilla de checklist: la administra el supervisor, una por tipo de trabajo."""
    _name = 'security.checklist.template'
    _description = 'Plantilla de Checklist por Tipo de Trabajo'
    _order = 'tipo_trabajo, id'

    name = fields.Char(string='Nombre', required=True)
    tipo_trabajo = fields.Selection(
        selection=TIPO_TRABAJO_SELECTION,
        string='Tipo de Trabajo',
        required=True,
        help='Los reportes de este tipo reciben automáticamente estos puntos.',
    )
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        'security.checklist.template.line',
        'template_id',
        string='Puntos del Checklist',
        copy=True,
    )


class SecurityChecklistTemplateLine(models.Model):
    _name = 'security.checklist.template.line'
    _description = 'Punto de la Plantilla de Checklist'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'security.checklist.template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Punto a verificar', required=True)
    obligatorio = fields.Boolean(
        string='Obligatorio',
        default=True,
        help='Si es obligatorio, no se puede finalizar el reporte sin marcarlo.',
    )


class SecurityReportCheck(models.Model):
    """Punto del checklist de un reporte concreto (copia de la plantilla)."""
    _name = 'security.report.check'
    _description = 'Punto del Checklist del Reporte'
    _order = 'sequence, id'

    report_id = fields.Many2one(
        'security.report',
        string='Reporte',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Punto a verificar', required=True)
    obligatorio = fields.Boolean(string='Obligatorio', default=True)
    hecho = fields.Boolean(string='Hecho', default=False)

    def write(self, vals):
        # El técnico solo puede marcar o desmarcar puntos, y solo mientras el
        # reporte sea editable para él.
        if not self.env.su and not self.env['security.report']._is_supervisor():
            if set(vals) - {'hecho'}:
                raise AccessError(_('Solo puede marcar o desmarcar los puntos del checklist.'))
            if any(c.report_id.state not in TECNICO_EDITABLE_STATES for c in self):
                raise UserError(_(
                    'El reporte está pendiente de validación o validado: '
                    'el checklist ya no se puede modificar.'
                ))
        return super().write(vals)
