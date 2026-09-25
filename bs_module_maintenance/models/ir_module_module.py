import traceback

from odoo import Command, api, fields, models
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.parse_version import parse_version

INSTALLED_STATES = ('installed', 'to upgrade', 'to remove')
OPERATIONS = {
    'button_install': 'install',
    'button_upgrade': 'upgrade',
    'button_uninstall': 'uninstall',
}
# Action log of the module operation running in this process, per database.
# The registry reload that applies the operation picks it up in _register_hook.
_running_log_ids = {}


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    upgrade_status = fields.Selection(
        [
            ('outdated', 'Needs Upgrade'),
            ('downgrade', 'Older on Disk'),
            ('missing', 'Missing on Disk'),
        ],
        compute='_compute_upgrade_status',
        search='_search_upgrade_status',
    )
    # state and version as last recorded in the action log
    logged_state = fields.Char(readonly=True, copy=False)
    logged_version = fields.Char(readonly=True, copy=False)

    @api.depends('state', 'latest_version')
    def _compute_upgrade_status(self):
        for module in self:
            module.upgrade_status = module._get_upgrade_status()

    def _search_upgrade_status(self, operator, value):
        if operator != 'in':
            return NotImplemented
        flagged = {
            module.id: status
            for module in self.search([('state', 'in', INSTALLED_STATES)])
            if (status := module._get_upgrade_status())
        }
        domain = Domain('id', 'in', [module_id for module_id, status in flagged.items() if status in value])
        if False in value:
            domain |= Domain('id', 'not in', list(flagged))
        return domain

    def _button_immediate_function(self, function):
        dbname = self.env.cr.dbname
        Log = self.env['ir.module.action.log']
        log_id = Log._log_start(OPERATIONS.get(function.__name__, 'update'), self, 'ui' if request else 'script')
        _running_log_ids[dbname] = log_id
        try:
            result = super()._button_immediate_function(function)
        except Exception:
            Log._log_finish(log_id, error=traceback.format_exc())
            raise
        finally:
            _running_log_ids.pop(dbname, None)
        Log._log_finish(log_id)
        return result

    def _register_hook(self):
        super()._register_hook()
        registry = self.env.registry
        # the hook runs again when the registry re-sets up its models; log once
        if self.env.cr.readonly or getattr(registry, '_bs_module_maintenance_synced', False):
            return
        registry._bs_module_maintenance_synced = True
        self._sync_action_log(registry.updated_modules, _running_log_ids.get(self.env.cr.dbname))

    def _get_upgrade_status(self):
        self.ensure_one()
        if (
            self.state not in INSTALLED_STATES
            or self.name == 'studio_customization'
            or ('imported' in self._fields and self.imported)
        ):
            return False
        if not self.get_module_info(self.name):
            return 'missing'
        if not self.latest_version:
            return False
        disk_version = parse_version(self.installed_version)
        db_version = parse_version(self.latest_version)
        if disk_version > db_version:
            return 'outdated'
        if disk_version < db_version:
            return 'downgrade'
        return False

    @api.model
    def _sync_action_log(self, updated_names, running_log_id=False):
        """Record module changes since the last sync in the action log.

        Installs and upgrades come from ``updated_names`` (the modules the registry
        loaded in update mode); uninstalls from the recorded state.
        """
        # workers loading the registry at the same time must not log twice
        self.env.cr.execute("SELECT pg_advisory_xact_lock(hashtext('bs_module_maintenance_sync'))")
        if not self.search_count([('logged_state', '!=', False)], limit=1):
            # first run after install: take the current state as the baseline
            self.search([('state', '=', 'installed')])._update_logged_values()
            return

        updated = self.search([('name', 'in', updated_names), ('state', '=', 'installed')])
        removed = self.search([('logged_state', '=', 'installed'), ('state', 'not in', INSTALLED_STATES)])
        if not updated and not removed:
            return

        lines = [module._get_log_line_values() for module in updated]
        lines += [
            {'module_name': module.name, 'change': 'uninstall', 'version_before': module.logged_version}
            for module in removed
        ]
        vals = {
            'line_ids': [Command.create(line) for line in lines],
            'date_end': fields.Datetime.now(),
        }
        Log = self.env['ir.module.action.log'].sudo()
        log = Log.browse(running_log_id).exists() if running_log_id else Log
        if log:
            # state is set by _button_immediate_function once the operation returns
            log.write(vals)
        else:
            Log.create({**vals, 'operation': 'update', 'source': 'server', 'state': 'done'})
        (updated | removed)._update_logged_values()

    def _get_log_line_values(self):
        self.ensure_one()
        version_before = self.logged_version if self.logged_state == 'installed' else False
        if not version_before:
            change = 'install'
        elif parse_version(self.latest_version) > parse_version(version_before):
            change = 'upgrade'
        elif parse_version(self.latest_version) < parse_version(version_before):
            change = 'downgrade'
        else:
            change = 'update'
        return {
            'module_name': self.name,
            'change': change,
            'version_before': version_before,
            'version_after': self.latest_version,
        }

    def _update_logged_values(self):
        for (state, version), modules in self.grouped(lambda m: (m.state, m.latest_version)).items():
            modules.write({'logged_state': state, 'logged_version': version})
