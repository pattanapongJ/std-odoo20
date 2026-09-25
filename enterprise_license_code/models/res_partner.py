from datetime import timedelta

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_enterprise_license_code(self, days=30):
        extend_date = fields.Date.today() + timedelta(days=days)
        self.env['ir.config_parameter'].sudo().set_str('database.expiration_date', str(extend_date))
