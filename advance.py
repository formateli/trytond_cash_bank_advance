# This file is part of Cash & Bank Advance module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.modules.currency.fields import Monetary
from decimal import Decimal


class Advance(ModelSQL, ModelView):
    "Collected/Paid in Advanced"
    __name__ = "cash_bank.advance"

    _states = {
        'readonly': True,
        }

    receipt_line = fields.Many2One('cash_bank.receipt.line', 'Receipt Line',
        required=True, ondelete='CASCADE', select=True,
        states={'readonly': True})
    company = fields.Function(
        fields.Many2One('company.company', 'Company'),
        'on_change_with_company', searcher='search_company')
    date = fields.Function(fields.Date('Date'),
        'on_change_with_date')
    party = fields.Function(
        fields.Many2One('party.party', 'Party'),
        'on_change_with_party', searcher='search_party')
    currency = fields.Function(
        fields.Many2One('currency.currency', 'Currency'),
        'on_change_with_currency', searcher='search_currency')
    type = fields.Selection([
        ('in', 'Collected in Advanced'),
        ('out', 'Paid in Advanced'),
        ], 'Type', required=True, states=_states)
    advance_type = fields.Selection([
        (None, ''),
        ('advance', 'In Advanced'),
        ('loan', 'Loan'),
        ], 'Advance Type')
    origin = fields.Reference('Origin', selection='get_origin')
    amount = fields.Function(Monetary('Amount',
        digits='currency', currency='currency'),
        'get_amount')
    amount_applied = fields.Function(Monetary('Amount Applied',
        digits='currency', currency='currency'),
        'get_amount_applied')
    amount_to_apply = fields.Function(Monetary('Amount to Apply',
        digits='currency', currency='currency'),
        'get_amount_to_apply')
    lines_applied = fields.One2Many('cash_bank.advance.line_applied',
        'advance', 'Lines Applied',
        states={
            'readonly': True,
        })
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('applied', 'Applied'),
        ('cancel', 'Canceled'),
        ], 'State', readonly=True, required=True)

    del _states

    @classmethod
    def __setup__(cls):
        super(Advance, cls).__setup__()
        cls._order = [
                ('receipt_line.receipt.date', 'DESC'),
                ('id', 'DESC'),
                ]

    @staticmethod
    def default_state():
        return 'draft'

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

    def _get_line_amount(self, line):
        res = Decimal('0.0')
        if line and line.line_move:
            res = line.line_move.debit - line.line_move.credit
        return abs(res)

    def get_amount(self, name):
        return self._get_line_amount(self.receipt_line)

    def get_amount_applied(self, name):
        res = Decimal('0.0')
        for line in self.lines_applied:
            res += self._get_line_amount(line.receipt_line)
        return res

    def get_amount_to_apply(self, name):
        return self.amount - self.amount_applied

    @fields.depends('receipt_line',
                    '_parent_receipt_line.receipt')
    def on_change_with_company(self, name=None):
        if self.receipt_line:
            return self.receipt_line.receipt.company.id

    @classmethod
    def search_company(cls, name, clause):
        return [('receipt_line.receipt.company', clause[1], clause[2])]

    @fields.depends('receipt_line',
                    '_parent_receipt_line.currency')
    def on_change_with_currency(self, name=None):
        if self.receipt_line:
            return self.receipt_line.currency.id

    @classmethod
    def search_currency(cls, name, clause):
        return [('receipt_line.receipt.currency', clause[1], clause[2])]

    @fields.depends('receipt_line',
                    '_parent_receipt_line.receipt')
    def on_change_with_date(self, name=None):
        if self.receipt_line and self.receipt_line.receipt:
            return self.receipt_line.receipt.date

    @fields.depends('receipt_line',
                    '_parent_receipt_line.party')
    def on_change_with_party(self, name=None):
        if self.receipt_line and self.receipt_line.party:
            return self.receipt_line.party.id

    @classmethod
    def search_party(cls, name, clause):
        return [('receipt_line.party', clause[1], clause[2])]

    def get_rec_name(self, name):
        return self.receipt_line.rec_name + '-' + str(self.id)

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('self.receipt_line.rec_name',) + tuple(clause[1:])]

    def get_reconcile_lines_for_amount(self, amount):
        lines = [self.receipt_line.line_move]
        for line in self.lines_applied:
            lines.append(line.receipt_line.line_move)
        return lines, self.amount_to_apply - amount


class AdvanceLineApplied(ModelSQL, ModelView):
    "Advance Line Applied"
    __name__ = "cash_bank.advance.line_applied"
    advance = fields.Many2One('cash_bank.advance', 'Advance',
        required=True, ondelete='CASCADE', select=True)
    receipt_line = fields.Many2One('cash_bank.receipt.line', 'Receipt Line',
        required=True, ondelete='RESTRICT', select=True,
        states={'readonly': True})
    date = fields.Function(fields.Date('Date'),
        'on_change_with_date')
    currency = fields.Function(
        fields.Many2One('currency.currency', 'Currency'),
        'on_change_with_currency')
    amount = fields.Function(Monetary('Amount',
        digits='currency', currency='currency'),
        'get_amount')

    @fields.depends('receipt_line',
                    '_parent_receipt_line.receipt')
    def on_change_with_date(self, name=None):
        if self.receipt_line and self.receipt_line.receipt:
            return self.receipt_line.receipt.date

    @fields.depends('receipt_line',
                    '_parent_receipt_line.currency')
    def on_change_with_currency(self, name=None):
        if self.receipt_line:
            return self.receipt_line.currency.id

    def get_amount(self, name):
        res = Decimal('0.0')
        if self.receipt_line and self.receipt_line.line_move:
            res = \
                self.receipt_line.line_move.debit \
                - self.receipt_line.line_move.credit
        return abs(res)
