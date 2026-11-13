# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .security_report import TECNICO_EDITABLE_STATES


class SecurityReportLine(models.Model):
    _name = 'security.report.line'
    _description = 'Línea de Equipo / Material del Reporte Técnico'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)

    report_id = fields.Many2one(
        'security.report',
        string='Reporte',
        required=True,
        ondelete='cascade',
        index=True,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        help='Opcional. Si no existe en el catálogo, escriba la descripción a mano.',
    )

    name = fields.Char(
        string='Descripción',
        compute='_compute_name',
        store=True,
        readonly=False,
        required=True,
    )

    cantidad = fields.Float(
        string='Cantidad',
        default=1.0,
        digits='Product Unit of Measure',
    )

    numero_serie = fields.Char(
        string='N° de Serie',
        help='Serie o MAC del equipo instalado, retirado o reemplazado.',
    )

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name

    # ==========================================
    # SEGURIDAD: mismo bloqueo que el reporte
    # ==========================================

    def _check_report_editable(self, reports):
        """Un técnico no puede tocar las líneas de un reporte en revisión o validado."""
        if self.env.su or self.env['security.report']._is_supervisor():
            return
        if any(report.state not in TECNICO_EDITABLE_STATES for report in reports):
            raise UserError(_(
                'El reporte está pendiente de validación o validado: '
                'sus equipos y materiales ya no se pueden modificar.'
            ))

    @api.model_create_multi
    def create(self, vals_list):
        reports = self.env['security.report'].browse(
            [vals['report_id'] for vals in vals_list if vals.get('report_id')]
        )
        self._check_report_editable(reports)
        return super().create(vals_list)

    def write(self, vals):
        self._check_report_editable(self.report_id)
        if vals.get('report_id'):
            self._check_report_editable(
                self.env['security.report'].browse(vals['report_id'])
            )
        return super().write(vals)

    def unlink(self):
        self._check_report_editable(self.report_id)
        return super().unlink()
