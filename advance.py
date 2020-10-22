# This file is part of Cash & Bank Advance module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.


class Advance(ModelSQL, ModelView):
    "Collected/Paid in Advanced"
    __name__ = "cash_bank.advance"
    receipt_line = fields.Many2One('cash_bank.receipt.line', 'Receipt Line',
        required=True, ondelete='CASCADE', select=True)
    type = fields.Selection([
        ('in', 'Collected in Advanced to Customer'),
        ('out', 'Paid in Advanced to Supplier'),
        ], 'Type', required=True)
    origin = fields.Reference('Origin', selection='get_origin')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('applied', 'Applied'),
        ('cancel', 'Canceled'),
        ], 'State', readonly=True, required=True)

    @classmethod
    def _get_origin(cls):
        return ['account.invoice']

    @classmethod
    def get_origin(cls):
        Model = Pool().get('ir.model')
        models = cls._get_origin()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [('', '')] + [(m.model, m.name) for m in models]
