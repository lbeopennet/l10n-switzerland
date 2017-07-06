# -*- coding: utf-8 -*-
# Copyright 2017 Open Net Sàrl
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import time

from openerp.tools.translate import _
from openerp import models, fields, exceptions, api

class Camt054ImportWizard(models.TransientModel):

    _name = 'camt054.import.wizard'

    camt054file = fields.Binary('Camt.054 File')


    @api.multi
    def import_camt054(self):
        if not self.camt054file:
            raise exceptions.UserError(
                _('Please select a file first!')
            )
        statement_id = self.env.context.get('active_id')
        if not statement_id:
            raise ValueError('The id of current satement is not in statement')

        parser = self.env['account.bank.statement.import.camt.parser']
        statement_line_obj = self.env['account.bank.statement.line']

        stmts_vals = parser.parse(base64.b64decode(self.camt054file))[2]
        lines_vals = []
        for stmt_vals in stmts_vals:
            lines_vals.extend(stmt_vals['transactions'])

        for l in lines_vals:
            self._match_ref(l)
            l['statement_id'] = statement_id
            statement_line_obj.create(l)

        self.env['ir.attachment'].create(
            {
                'name': 'Camt.054 %s' % time.strftime(
                    "%Y-%m-%d_%H:%M:%S", time.gmtime()
                ),
                'datas': self.camt054file,
                'datas_fname': 'camt054-%s.xml' % time.strftime(
                    "%Y-%m-%d_%H:%M:%S", time.gmtime()
                ),
                'res_model': 'account.bank.statement',
                'res_id': statement_id,
            },
        )
        return {}

    def _match_ref(self, line_vals):
        """try to find an invoice based on ISR references.

        Adapted from l10n_ch_payment_slip/wizard/bvr_import.py line 160.
        """
        ref, ref_type = line_vals.get('ref'), line_vals.get('camt_ref_type')
        if ref_type != "ISR Reference":
            return
        line = self.env['account.move.line'].search(
            [('transaction_ref', '=', ref),
             ('reconciled', '=', False),
             ('account_id.user_type_id.type', 'in', ['receivable', 'payable']),
             ('journal_id.type', '=', 'sale'),
             ],
            order='date desc',
        )
        if len(line) > 1:
            _logger.warning(
                _("Too many receivable/payable lines for reference %s") % ref)
            return

        if line:
            # transaction_ref is propagated on all lines
            partner_id = line.partner_id.id
            num = line.invoice_id.number if line.invoice_id else False
            if num:
                line_vals['name'] = line_vals['ref']
                line_vals['ref'] = _('Inv. no %s') % num
            line_vals['partner_id'] = partner_id
