# This file is part of Cash & Bank Advance module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart
from trytond.modules.cash_bank.tests import (
    create_bank_account, create_cash_bank, create_sequence,
    create_journal, create_fiscalyear)
import datetime
from decimal import Decimal


class AdvanceTestCase(ModuleTestCase):
    'Test Cash Bank Advance module'
    module = 'cash_bank_advance'

    @with_transaction()
    def test_advance(self):
        pool = Pool()
        Account = pool.get('account.account')
        Config = pool.get('cash_bank.configuration')
        Receipt = pool.get('cash_bank.receipt')
        Advance = pool.get('cash_bank.advance')
        AdvanceLineApplied = pool.get('cash_bank.advance.line_applied')

        party = self._create_party('Party test', None)

        transaction = Transaction()

        company = create_company()
        with set_company(company):
            create_chart(company)
            create_fiscalyear(company)

            account_cash, = Account.search([
                    ('name', '=', 'Main Cash'),
                    ])
            account_revenue, = Account.search([
                    ('name', '=', 'Main Revenue'),
                    ])
            account_expense, = Account.search([
                    ('name', '=', 'Main Expense'),
                    ])
            account_receivable, = Account.search([
                    ('name', '=', 'Main Receivable'),
                    ])
            account_payable, = Account.search([
                    ('name', '=', 'Main Payable'),
                    ])

            config = Config(
                default_collected_in_advanced_account=account_payable,
                default_paid_in_advanced_account=account_receivable)
            config.save()

            journal = create_journal(company, 'journal_cash')

            sequence = create_sequence(
                'Cash/Bank Sequence',
                'Cash and Bank Receipt',
                company)
            sequence_convertion = create_sequence(
                'Cash/Bank Convertion',
                'Cash and Bank Convertion',
                company)

            config.convertion_seq = sequence_convertion
            config.save()

            cashier = create_cash_bank(
                company, 'Main Cash', 'cash',
                journal, account_cash, sequence,
                )

            date = datetime.date.today()

            # Test Collected in advance from Customer
            self._basic_advance(company, cashier, 'in', date,
                    party, account_payable, account_expense)

            # Test Paid in advance to Supplier
            self._basic_advance(company, cashier, 'out', date,
                    party, account_receivable, account_expense)

    def _basic_advance(self, company, cashier, type_, date, party,
                account, second_account):
        pool = Pool()
        Receipt = pool.get('cash_bank.receipt')
        Advance = pool.get('cash_bank.advance')

        if type_ == 'in':
            type_create = 'advance_in_create'
            type_apply = 'advance_in_apply'
            type_inverse = 'out'
        else:
            type_create = 'advance_out_create'
            type_apply = 'advance_out_apply'
            type_inverse = 'in'

        # Create an advance type of 'type_create'

        receipt = self._get_receipt(company, cashier,
                type_, date, Decimal('100.0'), party)
        receipt.lines = [
            self._get_receipt_line(
                account, Decimal('100.0'),
                type_=type_create,
                party=party),
            ]
        receipt.save()

        # Advance is created when receipt is confirmed
        self.assertEqual(receipt.lines[0].advance, None)

        Receipt.confirm([receipt])
        advance = receipt.lines[0].advance
        self.assertEqual(advance.state, 'confirmed')
        self.assertEqual(advance.receipt_line, receipt.lines[0])

        Receipt.post([receipt])
        self.assertEqual(advance.state, 'pending')
        self.assertEqual(advance.amount_applied, Decimal('0.0'))
        self.assertEqual(advance.amount_to_apply, Decimal('100.0'))

        # Apply partially

        receipt = self._get_receipt(company, cashier,
                type_, date, Decimal('130.0'), party)
        receipt.lines = [
                self._get_receipt_line(
                    account, Decimal('-70.0'),
                    type_=type_apply,
                    advance=advance,
                    party=party),
                self._get_receipt_line(
                    second_account, Decimal('200.0')),
                ]
        receipt.save()
        Receipt.confirm([receipt])
        Receipt.post([receipt])
        self.assertEqual(advance.state, 'pending')
        self.assertEqual(advance.amount_applied, Decimal('70.0'))
        self.assertEqual(advance.amount_to_apply, Decimal('30.0'))

        # Try to over apply

        receipt = self._get_receipt(company, cashier,
                type_, date, Decimal('120.0'), party)
        with self.assertRaises(UserError):
            receipt.lines = [
                self._get_receipt_line(
                    account, Decimal('-80.0'),
                    type_=type_apply,
                    advance=advance,
                    party=party),
                self._get_receipt_line(
                    second_account, Decimal('200.0')),
                ]
            receipt.save()
            Receipt.confirm([receipt])
        Receipt.delete([receipt])

        # Apply completly
        receipt = self._get_receipt(company, cashier,
                type_, date, Decimal('170.0'), party)
        receipt.lines = [
                self._get_receipt_line(
                    account, Decimal('-30.0'),
                    type_=type_apply,
                    advance=advance,
                    party=party),
                self._get_receipt_line(
                    second_account, Decimal('200.0')),
                ]
        receipt.save()

        Receipt.confirm([receipt])
        Receipt.post([receipt])
        self.assertEqual(advance.state, 'applied')
        self.assertEqual(advance.amount_applied, Decimal('100.0'))
        self.assertEqual(advance.amount_to_apply, Decimal('0.0'))

        # Create an advance with wrong sign in create

        Advance.delete(Advance.search([]))

        receipt = self._get_receipt(company, cashier,
                type_, date, Decimal('200.0'), party)
        with self.assertRaises(UserError):
            receipt.lines = [
                self._get_receipt_line(
                    account, Decimal('-200.0'),
                    type_=type_create,
                    party=party),
                self._get_receipt_line(
                    second_account, Decimal('400.0')),
                ]
            receipt.save()
            Receipt.confirm([receipt])
            Receipt.post([receipt])
        Receipt.cancel([receipt])
        Receipt.draft([receipt])
        Receipt.delete([receipt])

        receipt = self._get_receipt(company, cashier,
                type_inverse, date, Decimal('200.0'), party)
        with self.assertRaises(UserError):
            receipt.lines = [
                self._get_receipt_line(
                    account, Decimal('400.0'),
                    type_=type_create,
                    party=party),
                self._get_receipt_line(
                    second_account, Decimal('-200.0')),
                ]
            receipt.save()
            Receipt.confirm([receipt])
            Receipt.post([receipt])
        Receipt.cancel([receipt])
        Receipt.draft([receipt])
        Receipt.delete([receipt])

        Advance.delete(Advance.search([]))

        receipt = self._get_receipt(company, cashier,
                type_inverse, date, Decimal('200.0'), party)
        receipt.lines = [
                self._get_receipt_line(
                    account, Decimal('-200.0'), # Correct sign
                    type_=type_create,
                    party=party),
                self._get_receipt_line(
                    second_account, Decimal('400.0')),
            ]
        receipt.save()
        Receipt.confirm([receipt])
        Receipt.post([receipt])

        advance = Advance.search([])[0]
        self.assertEqual(advance.amount, Decimal('200.0'))
        self.assertEqual(advance.amount_applied, Decimal('0.0'))
        self.assertEqual(advance.amount_to_apply, Decimal('200.0'))
        self.assertEqual(advance.state, 'pending')

        # Apply an advance with wrong sign in apply

        receipt = self._get_receipt(company, cashier,
                type_, date, Decimal('100.0'), party)
        with self.assertRaises(UserError):
            receipt.lines = [
                    self._get_receipt_line(
                        account, Decimal('200.0'),
                        type_=type_apply,
                        advance=advance,
                        party=party),
                    self._get_receipt_line(
                        second_account, Decimal('-100.0')),
                    ]
            receipt.save()
            Receipt.confirm([receipt])
            Receipt.post([receipt])
        Receipt.cancel([receipt])
        Receipt.draft([receipt])
        Receipt.delete([receipt])

        receipt = self._get_receipt(company, cashier,
                type_inverse, date, Decimal('100.0'), party)
        with self.assertRaises(UserError):
            receipt.lines = [
                    self._get_receipt_line(
                        account, Decimal('-200.0'),
                        type_=type_apply,
                        advance=advance,
                        party=party),
                    self._get_receipt_line(
                        second_account, Decimal('300.0')),
                    ]
            receipt.save()
            Receipt.confirm([receipt])
            Receipt.post([receipt])
        Receipt.cancel([receipt])
        Receipt.draft([receipt])
        Receipt.delete([receipt])

        receipt = self._get_receipt(company, cashier,
                type_inverse, date, Decimal('100.0'), party)
        receipt.lines = [
                self._get_receipt_line(
                    account, Decimal('200.0'), # Correct sign
                    type_=type_apply,
                    advance=advance,
                    party=party),
                self._get_receipt_line(
                    second_account, Decimal('-100.0')),
            ]
        receipt.save()
        Receipt.confirm([receipt])
        Receipt.post([receipt])
        self.assertEqual(advance.amount, Decimal('200.0'))
        self.assertEqual(advance.amount_applied, Decimal('200.0'))
        self.assertEqual(advance.amount_to_apply, Decimal('0.0'))
        self.assertEqual(advance.state, 'applied')

        # Test Delete

        advances = Advance.search([])
        Advance.delete(advances)

        receipt = self._get_receipt(company, cashier,
                type_, date, Decimal('100.0'), party)
        receipt.lines = [
            self._get_receipt_line(
                account, Decimal('100.0'),
                type_=type_create,
                party=party),
            ]
        receipt.save()
        Receipt.confirm([receipt])
        advances = Advance.search([])
        self.assertEqual(len(advances), 1)

        Receipt.cancel([receipt]) # Here advance is deleted
        advances = Advance.search([])
        self.assertEqual(len(advances), 0)

        Receipt.draft([receipt])
        Receipt.delete([receipt])

    def _get_receipt(self, company, cash_bank,
                    receipt_type, date, amount, party):
        pool = Pool()
        Receipt = pool.get('cash_bank.receipt')
        ReceiptType = pool.get('cash_bank.receipt_type')

        type_ = ReceiptType.search([
            ('cash_bank', '=', cash_bank.id),
            ('type', '=', receipt_type)])[0]

        receipt = Receipt(
            company=company,
            cash_bank=cash_bank,
            party=party,
            type=type_,
            date=date,
            cash=amount,
            )

        return receipt

    def _get_receipt_line(self, account, amount,
                type_='move_line', party=None,
                advance=None):
        pool = Pool()
        Line = pool.get('cash_bank.receipt.line')
        line = Line(
            type=type_,
            party=party,
            account=account,
            amount=amount,
            advance=advance
            )
        return line

    @classmethod
    def _create_party(cls, name, account):
        pool = Pool()
        Party = pool.get('party.party')
        Address = pool.get('party.address')
        addr = Address(name=name)
        party = Party(
            name=name,
            account_receivable=account,
            addresses=[addr]
            )
        party.save()
        return party

del ModuleTestCase
