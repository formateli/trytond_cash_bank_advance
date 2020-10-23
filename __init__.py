# This file is part of Cash & Bank Advanced module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import configuration
from . import advance
from . import receipt


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationAccount,
        advance.Advance,
        advance.AdvanceLineApplied,
        receipt.Receipt,
        receipt.ReceiptLine,
        module='cash_bank_advance', type_='model')
