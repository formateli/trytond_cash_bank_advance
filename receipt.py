# This file is part of Cash & Bank Advance module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.model import fields
from trytond.pyson import Eval, In, If, Not, Or, Bool


class Receipt(metaclass=PoolMeta):
    __name__ = 'cash_bank.receipt'

    @classmethod
    def _advance_confirm(cls, line):
        pool = Pool()
        Advance = pool.get('cash_bank.advance')

        if line.type not in ['advance_in_create', 'advance_out_create']:
            return

        if line.advance:
            advance = line.advance
        else:
            if line.type == 'advance_in_create':
                type_ = 'in'
            else:
                type_ = 'out'

            advance = Advance(
                receipt_line=line,
                type=type_,
                )

        advance.origin = line.advance_origin
        advance.state = 'confirmed'
        advance.save()

        if not line.advance or line.advance != advance:
            line.advance = advance
            line.save()

    @classmethod
    def _set_advance_state(cls, lines, state):
        Advance = Pool().get('cash_bank.advance')
        to_update = []
        for line in lines:
            if not line.advance:
                return
            if line.advance.state == 'applied':
                return
            if line.type not in ['advance_in_create', 'advance_out_create']:
                return
            line.advance.state = state
            to_update.append(line.advance)
        Advance.save(to_update)

    @classmethod
    def draft(cls, receipts):
        super(Receipt, cls).draft(receipts)
        for receipt in receipts:
            cls._set_advance_state(receipt.lines, 'draft')

    @classmethod
    def cancel(cls, receipts):
        super(Receipt, cls).cancel(receipts)
        for receipt in receipts:
            cls._set_advance_state(receipt.lines, 'cancel')

    @classmethod
    def confirm(cls, receipts):
        super(Receipt, cls).confirm(receipts)
        for receipt in receipts:
            for line in receipt.lines:
                cls._advance_confirm(line)

    @classmethod
    def post(cls, receipts):
        super(Receipt, cls).post(receipts)
        for receipt in receipts:
            cls._set_advance_state(receipt.lines, 'pending')


class ReceiptLine(metaclass=PoolMeta):
    __name__ = 'cash_bank.receipt.line'
    advance = fields.Many2One('cash_bank.advance', 'Advance',
        domain=[
            If(In(Eval('type'), ['advance_in_apply',
                                 'advance_in_create',
                                 'advance_out_apply',
                                 'advance_out_create']),
                If(In(Eval('type'), ['advance_in_apply',
                                     'advance_out_apply']),
                    [('company', '=', Eval(
                            '_parent_receipt', {}).get('company', -1)),
                    ('state', '=', 'pending'),
                    ('currency', '=', Eval(
                            '_parent_receipt', {}).get('currency', -1)),
                    ('party', '=', Eval('party')),
                    If(Eval('type') == 'advance_in_apply',
                        ('type', '=', 'in'),
                        ('type', '=', 'out')
                    )],
                    [('id', '!=', -1)]
                ),
                [('id', '=', -1)],
            ),
        ],
        states={
            'readonly': Eval('receipt_state') != 'draft',
            'invisible': Not(In(
                Eval('type'), ['advance_in_apply', 'advance_out_apply']))
        },
        depends=['receipt_state', 'party', 'account', 'type'])
    advance_origin = fields.Reference(
        'Origin', selection='get_advance_origin',
        states={
            'readonly': Eval('receipt_state') != 'draft',
            'invisible': Not(
                In(Eval('type'), ['advance_in_create', 'advance_out_create']))
        }, depends=['receipt_state', 'type'])

    @classmethod
    def __setup__(cls):
        super(ReceiptLine, cls).__setup__()
        cls.type.selection += [
            ('advance_in_apply', 'Apply Collected in Advanced from Customer'),
            ('advance_in_create', 'Create Collected in Advance from Customer'),
            ('advance_out_apply', 'Apply Paid in Advanced to Supplier'),
            ('advance_out_create', 'Create Paid in Advance to Supplier'),
            ]

        cls.party.states['readonly'] = Or(
                    Eval('receipt_state') != 'draft',
                    Bool(Eval('invoice')),
                    Bool(Eval('advance')),
                )
        cls.party.depends += ['advance']

        cls.account.states['readonly'] = Or(
                Eval('receipt_state') != 'draft',
                Not(In(Eval('type'), [
                    'move_line',
                    'advance_in_create',
                    'advance_out_create'
                    ])),
                )

        cls.account.domain.append(
                If (In(Eval('type'),
                        ['advance_in_create', 'advance_out_create']),
                    [
                        ('reconcile', '=', True),
                        ('party_required', '=', True)
                    ],
                    []
                )
            )

    @classmethod
    def get_advance_origin(cls):
        pool = Pool()
        Model = pool.get('ir.model')
        Advance = pool.get('cash_bank.advance')
        models = Advance._get_origin()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [('', '')] + [(m.model, m.name) for m in models]

    @fields.depends('party', 'type')
    def on_change_party(self):
        pool = Pool()
        Config = pool.get('cash_bank.configuration')
        if self.party and self.type and \
                self.type in ['advance_in_create', 'advance_out_create']:
            config = Config(1)
            if self.type == 'advance_in_create':
                self.account = config.default_collected_in_advanced_account
            else:
                self.account = config.default_paid_in_advanced_account

    @fields.depends('type')
    def on_change_type(self):
        super(ReceiptLine, self).on_change_type()
        self.advance = None
        self.advance_origin = None

    @fields.depends('advance', 'receipt',
                    '_parent_receipt.type')
    def on_change_advance(self):
        if self.advance:
            self.amount = self.advance.amount_to_apply
            self.account = self.advance.receipt_line.account
            if self.receipt:
                if self.receipt.type.type == 'in':
                    if self.advance.type == 'in':
                        self.amount *= -1
                else:
                    if self.advance.type == 'out':
                        self.amount *= -1

    def validate_line(self):
        super(ReceiptLine, self).validate_line()
        pool = Pool()
        Currency = pool.get('currency.currency')
        if self.advance:
            with Transaction().set_context(date=self.advance.date):
                amount_to_apply = Currency.compute(self.advance.currency,
                    self.advance.amount_to_apply,
                    self.receipt.currency)

            if self.receipt.type.type == 'in':
                if self.advance.type == 'in' and \
                        self.type == 'advance_in_create':
                    amount_to_apply = 1
                elif self.advance.type == 'in' and \
                        self.type == 'advance_out_create':
                    amount_to_apply = -1
                elif self.advance.type == 'in' and \
                        self.type == 'advance_in_apply':
                    amount_to_apply *= -1
                elif self.advance.type == 'out' and \
                        self.type == 'advance_out_create':
                    amount_to_apply = -1
            else:
                if self.advance.type == 'out' and \
                        self.type == 'advance_out_create':
                    amount_to_apply = 1
                elif self.advance.type == 'out' and \
                        self.type == 'advance_in_create':
                    amount_to_apply = -1
                elif self.advance.type == 'out' and \
                        self.type == 'advance_out_apply':
                    amount_to_apply *= -1
                elif self.advance.type == 'in' and \
                        self.type == 'advance_in_create':
                    amount_to_apply = -1

            check_greater = True
            if self.type in \
                    ['advance_in_create', 'advance_out_create']:
                check_greater = False
                
            self._check_invalid_amount(amount_to_apply,
                    self.advance.rec_name, check_greater=check_greater)

    def reconcile(self):
        super(ReceiptLine, self).reconcile()
        pool = Pool()
        Currency = pool.get('currency.currency')
        AdvanceLine = pool.get('cash_bank.advance.line_applied')
        MoveLine = pool.get('account.move.line')

        if self.advance:
            if self.type in \
                    ['advance_in_create', 'advance_out_create']:
                return

            with Transaction().set_context(date=self.advance.date):
                amount = Currency.compute(self.receipt.currency,
                    self.amount, self.receipt.company.currency)

            amount_to_reconcile = abs(amount)
            reconcile_lines, remainder = \
                self.advance.get_reconcile_lines_for_amount(
                    amount_to_reconcile)

            line_applied = AdvanceLine(
                advance=self.advance,
                receipt_line=self
                )
            line_applied.save()

            if remainder == 0:
                lines = reconcile_lines + [self.line_move]
                MoveLine.reconcile(lines)
                self.advance.state = 'applied'
                self.advance.save()
