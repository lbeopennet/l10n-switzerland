# -*- coding: utf-8 -*-
# copyright 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Switzerland - PAIN Credit Transfer",
    "summary": "Generate ISO 20022 credit transfert (SEPA and not SEPA)",
    "version": "10.0.1.0.0",
    "category": "Finance",
    "author": "Akretion,Camptocamp,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "l10n_ch_pain_base",
        "account_banking_sepa_credit_transfer",
    ],
    'installable': True,
}
