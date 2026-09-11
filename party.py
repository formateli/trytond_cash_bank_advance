# This file is part of rrhh_loan module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import PoolMeta
from trytond.model import fields


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    loans = fields.One2Many('cash_bank.advance',
        'party', 'Loans',
        states={'readonly': True},
        filter=[('state', 'in', ['pending', 'applied'])]
        )