# -*- coding: utf-8 -*-
{
    'name': 'Reportes Técnicos de Seguridad',
    'version': '17.0.1.4.0',
    'summary': 'Registro de trabajos técnicos de campo: instalaciones, mantenimientos, reparaciones',
    'description': """
Reportes Técnicos de Seguridad
==============================

Módulo para registrar y gestionar los trabajos técnicos realizados
por técnicos de campo: instalaciones de cámaras, mantenimientos,
reparaciones y diagnósticos.

* Flujo: borrador, programado, en proceso, finalizado, validado / rechazado.
* Evidencia obligatoria: descripción, fotos y firma del cliente.
* Control de tiempos de llegada y salida.
* Líneas de equipos y materiales con producto, cantidad y serie.
* Historial (chatter) y avisos al supervisor y al técnico.
* Informe PDF para entregar al cliente.
* Vistas kanban, calendario (agenda), gráfico y tabla dinámica.
* Checklist por tipo de trabajo, obligatorio para finalizar.
* Ubicación GPS al iniciar y finalizar el trabajo.
    """,
    'author': 'Forsemax',
    'category': 'Security',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'product'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'data/ir_sequence_data.xml',
        'data/checklist_data.xml',
        'report/security_report_report.xml',
        'views/security_report_views.xml',
        'views/security_checklist_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'security_reports/static/src/js/security_report_form.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
