from odoo.release import major_version
from odoo.tests import TransactionCase

OLD_VERSION = f'{major_version}.0.0.1'
NEW_VERSION = f'{major_version}.1.0'


class TestActionLog(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Module = cls.env['ir.module.module']
        cls.Log = cls.env['ir.module.action.log']
        cls.base = cls.Module.search([('name', '=', 'base')])
        # make sure a baseline exists, then start from a clean state
        cls.Module._sync_action_log([])
        cls.Module._sync_action_log([])

    def _sync(self, updated_names, running_log_id=False):
        before = self.Log.search([])
        self.Module._sync_action_log(updated_names, running_log_id)
        return self.Log.search([]) - before

    def test_nothing_changed(self):
        self.assertFalse(self._sync([]))

    def test_server_upgrade(self):
        self.base.logged_version = OLD_VERSION
        log = self._sync(['base'])
        self.assertRecordValues(log, [{'operation': 'update', 'source': 'server', 'state': 'done'}])
        self.assertRecordValues(log.line_ids, [{
            'module_name': 'base',
            'change': 'upgrade',
            'version_before': OLD_VERSION,
            'version_after': self.base.latest_version,
        }])
        self.assertEqual(self.base.logged_version, self.base.latest_version)
        # already recorded: the same registry load must not log it again
        self.assertFalse(self._sync([]))

    def test_same_version_update(self):
        log = self._sync(['base'])
        self.assertEqual(log.line_ids.change, 'update')

    def test_install_then_uninstall(self):
        module = self.Module.create({
            'name': 'bs_module_maintenance_fixture',
            'state': 'installed',
            'latest_version': NEW_VERSION,
        })
        log = self._sync(['bs_module_maintenance_fixture'])
        self.assertRecordValues(log.line_ids, [{'change': 'install', 'version_before': False, 'version_after': NEW_VERSION}])

        module.write({'state': 'uninstalled', 'latest_version': False})
        log = self._sync([])
        self.assertRecordValues(log.line_ids, [{
            'module_name': 'bs_module_maintenance_fixture',
            'change': 'uninstall',
            'version_before': NEW_VERSION,
        }])
        self.assertEqual(module.logged_state, 'uninstalled')

    def test_running_log_receives_changes(self):
        running = self.Log.create({'operation': 'upgrade', 'source': 'ui', 'requested_modules': 'base'})
        self.base.logged_version = OLD_VERSION
        self.assertFalse(self._sync(['base'], running.id), "no separate server log")
        self.assertEqual(running.line_ids.module_name, 'base')
        self.assertEqual(running.state, 'running', "the caller closes the log")
