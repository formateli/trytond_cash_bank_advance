# This file is part of Cash & Bank Advance module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
try:
    from \
        trytond.modules.cash_bank_advance.tests.test_advance \
        import suite
except ImportError:
    from .test_advance import suite

__all__ = ['suite']
