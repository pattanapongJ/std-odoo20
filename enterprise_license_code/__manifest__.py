{
    'name': 'Enterprise License Code',
    'description': 'Enterprise License Code Developed By Basic Solutions Co.,Ltd.',
    'depends': [
        'base',
        'web'
    ],
    'category': 'Technical',
    'installable': True,
    'auto_install': False,
    'application': True,
    'version': '20.0.0.2',
    'author': 'Basic Solution Co., Ltd.',
    'website': 'https://www.basic-solution.com',
    'license': 'LGPL-3',
    'data': [
        # XML files for views, security, etc. can be added here
        'data/scheduled_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'enterprise_license_code/static/src/scss/enterprise.scss',
            'enterprise_license_code/static/src/js/hide_expiration_panel.js'
        ]
    }
}
