# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
