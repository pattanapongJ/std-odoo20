from odoo import fields, models


class IrModuleActionLogLine(models.Model):
    _name = 'ir.module.action.log.line'
    _description = 'Module Action Log Line'
    _order = 'log_id, module_name'
    _rec_name = 'module_name'

    log_id = fields.Many2one('ir.module.action.log', required=True, ondelete='cascade', index=True)
    module_name = fields.Char('Module', required=True)
    change = fields.Selection(
        [
            ('install', 'Installed'),
            ('upgrade', 'Upgraded'),
            ('update', 'Updated, same version'),
            ('downgrade', 'Downgraded'),
            ('uninstall', 'Uninstalled'),
        ],
        required=True,
    )
    version_before = fields.Char()
    version_after = fields.Char()
