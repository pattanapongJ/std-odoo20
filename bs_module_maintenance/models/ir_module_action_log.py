from odoo import api, fields, models


class IrModuleActionLog(models.Model):
    _name = 'ir.module.action.log'
    _description = 'Module Action Log'
    _order = 'date_start desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    operation = fields.Selection(
        [
            ('install', 'Install'),
            ('upgrade', 'Upgrade'),
            ('uninstall', 'Uninstall'),
            ('update', 'Server Update'),
        ],
        required=True,
        readonly=True,
    )
    source = fields.Selection(
        [
            ('ui', 'User Interface'),
            ('script', 'Command Line / Script'),
            ('server', 'Server Start'),
        ],
        required=True,
        readonly=True,
    )
    user_id = fields.Many2one('res.users', readonly=True, ondelete='set null')
    requested_modules = fields.Char(readonly=True)
    state = fields.Selection(
        [('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')],
        required=True,
        default='running',
        readonly=True,
    )
    date_start = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    date_end = fields.Datetime(readonly=True)
    duration = fields.Float('Duration (s)', compute='_compute_duration', store=True, digits=(16, 1))
    error = fields.Text(readonly=True)
    line_ids = fields.One2many('ir.module.action.log.line', 'log_id', readonly=True)

    @api.depends('requested_modules', 'line_ids.module_name')
    def _compute_name(self):
        for log in self:
            log.name = log.requested_modules or ', '.join(log.line_ids.mapped('module_name'))

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for log in self:
            if log.date_start and log.date_end:
                log.duration = (log.date_end - log.date_start).total_seconds()
            else:
                log.duration = 0.0

    # The methods below use their own cursor: the module operation commits and
    # rolls back the caller's transaction, and the log must survive both.

    @api.model
    def _log_start(self, operation, modules, source):
        with self.env.registry.cursor() as cr:
            log = self.env(cr=cr, su=True)[self._name].create({
                'operation': operation,
                'source': source,
                'user_id': self.env.uid,
                'requested_modules': ', '.join(modules.mapped('name')),
            })
            return log.id

    @api.model
    def _log_finish(self, log_id, error=None):
        with self.env.registry.cursor() as cr:
            env = self.env(cr=cr, su=True)
            # the operation may have uninstalled this module
            if self._name not in env:
                return
            log = env[self._name].browse(log_id).exists().filtered(lambda log: log.state == 'running')
            # Changes are only committed once the registry reload succeeded: the
            # operation was applied and the error came from a later step (for
            # instance another module's override of _button_immediate_function).
            applied = bool(log.line_ids)
            if error and applied:
                error = "The module operation was applied, but a later step raised an error:\n\n" + error
            log.write({
                'state': 'failed' if error and not applied else 'done',
                'date_end': fields.Datetime.now(),
                'error': error,
            })
