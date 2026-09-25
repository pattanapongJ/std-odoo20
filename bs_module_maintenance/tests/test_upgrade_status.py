from odoo.release import major_version
from odoo.tests import TransactionCase

OLD_VERSION = f'{major_version}.0.0.1'
NEW_VERSION = f'{major_version}.1.0'


class TestUpgradeStatus(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Module = cls.env['ir.module.module']
        cls.base = cls.Module.search([('name', '=', 'base')])

    def _search_ids(self, domain):
        return set(self.Module.search(domain).ids)

    def test_outdated(self):
        self.base.latest_version = OLD_VERSION
        self.assertEqual(self.base.upgrade_status, 'outdated')
        self.assertIn(self.base.id, self._search_ids([('upgrade_status', '=', 'outdated')]))
        self.assertIn(self.base.id, self._search_ids([('upgrade_status', '!=', False)]))
        self.assertNotIn(self.base.id, self._search_ids([('upgrade_status', '=', False)]))

    def test_downgrade(self):
        self.base.latest_version = f'{major_version}.99.0'
        self.assertEqual(self.base.upgrade_status, 'downgrade')
        self.assertNotIn(self.base.id, self._search_ids([('upgrade_status', '=', 'outdated')]))

    def test_up_to_date(self):
        self.base.latest_version = self.base.installed_version
        self.assertFalse(self.base.upgrade_status)
        self.assertIn(self.base.id, self._search_ids([('upgrade_status', '=', False)]))
        self.assertNotIn(self.base.id, self._search_ids([('upgrade_status', '!=', False)]))

    def test_missing_on_disk(self):
        missing = self.Module.create({
            'name': 'bs_module_maintenance_missing_fixture',
            'state': 'installed',
            'latest_version': NEW_VERSION,
        })
        self.assertEqual(missing.upgrade_status, 'missing')
        self.assertIn(missing.id, self._search_ids([('upgrade_status', '=', 'missing')]))

    def test_not_installed(self):
        module = self.Module.create({'name': 'bs_module_maintenance_uninstalled_fixture', 'state': 'uninstalled'})
        self.assertFalse(module.upgrade_status)
        self.assertIn(module.id, self._search_ids([('upgrade_status', '=', False)]))
