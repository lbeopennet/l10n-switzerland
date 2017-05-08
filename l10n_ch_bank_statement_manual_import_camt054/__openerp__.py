# -*- coding: utf-8 -*-
# Copyright 2017 Open Net Sàrl
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Manual Camt.054 Import Wizard with BVR/ESR matching',
    'summary': 'Allows to manually import Swiss Camt.054 bank statements',
    'version': '9.0.1.0.0',
    'category': 'accounting',
    'website': 'https://odoo-community.org/',
    'author': 'Open Net Sàrl, Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'account_accountant',
        'account_bank_statement_import_camt_reftype',
    ],
    'data': [
        'wizard/camt054_import_view.xml',
    ],
}
