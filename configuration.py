# This file is part of Cash & Bank Advanced module.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from trytond.pyson import Eval


class Configuration(metaclass=PoolMeta):
    __name__ = 'cash_bank.configuration'
    default_collected_in_advanced_account = fields.MultiValue(
        fields.Many2One('account.account',
            'Default Collected in Advanced Account', required=True,
            domain=[
                ('company', '=', Eval('context', {}).get('company', -1)),
                ('type', '!=', None),
                ('closed', '!=', True),
                ('reconcile', '=', True),
                ('party_required', '=', True),
                ])
            )
    default_paid_in_advanced_account = fields.MultiValue(
        fields.Many2One('account.account',
            'Default Paid in Advanced Account', required=True,
            domain=[
                ('company', '=', Eval('context', {}).get('company', -1)),
                ('type', '!=', None),
                ('closed', '!=', True),
                ('reconcile', '=', True),
                ('party_required', '=', True),
                ])
            )

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in \
                {'default_collected_in_advanced_account',
                 'default_paid_in_advanced_account'}:
            return pool.get('cash_bank.configuration.account')
        return super(Configuration, cls).multivalue_model(field)


class ConfigurationAccount(metaclass=PoolMeta):
    __name__ = 'cash_bank.configuration.account'
    default_collected_in_advanced_account = fields.Many2One(
        'account.account', 'Default Collected in Advanced Account',
        domain=[
            ('company', '=', Eval('context', {}).get('company', -1)),
            ('type', '!=', None),
            ('closed', '!=', True),
            ('reconcile', '=', True),
            ('party_required', '=', True),
            ])
    default_paid_in_advanced_account = fields.Many2One(
        'account.account', 'Default Paid in Advanced Account',
        domain=[
            ('company', '=', Eval('context', {}).get('company', -1)),
            ('type', '!=', None),
            ('closed', '!=', True),
            ('reconcile', '=', True),
            ('party_required', '=', True),
            ])
