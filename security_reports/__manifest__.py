# -*- coding: utf-8 -*-
{
    'name': 'Reportes Técnicos de Seguridad',
    'version': '17.0.1.0.0',
    'summary': 'Registro de trabajos técnicos de campo: instalaciones, mantenimientos, reparaciones',
    'description': """
Reportes Técnicos de Seguridad
==============================

Módulo para registrar y gestionar los trabajos técnicos realizados
por técnicos de campo: instalaciones de cámaras, mantenimientos,
reparaciones y diagnósticos.
    """,
    'author': 'Tu Empresa',
    'category': 'Security',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'data/ir_sequence_data.xml',
        'views/security_report_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}