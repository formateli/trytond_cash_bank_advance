# This file is part of Cash & Bank Advance module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.pool import Pool


class AdvanceTestCase(ModuleTestCase):
    'Test Cash Bank Advance module'
    module = 'cash_bank_advance'

    @with_transaction()
    def test_advance(self):
        pool = Pool()
        Config = pool.get('cash_bank.configuration')
        Receipt = pool.get('cash_bank.receipt')
        Advance = pool.get('cash_bank.advance')
        AdvanceLineApplied = pool.get('cash_bank.advance.line_applied')


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AdvanceTestCase))
    return suite
