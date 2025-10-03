{
    'name': 'KES Inspections',
    'version': '1.0',
    'summary': 'Gestion des inspections techniques KES',
    'description': """
        Module de gestion complète des inspections techniques
        - Gestion des affaires et sous-affaires d'inspection
        - Assignation d'inspecteurs avec rôles spécifiques
        - Génération d'étiquettes QR Code par type d'intervention
        - Gestion des rapports PDF/Word et documents
        - Planning des inspecteurs
        - Alertes de prochaines inspections
    """,
    'author': 'Nague Justin',
    'category': 'Operations',
    'depends': ['base', 'sale', 'mail', 'sale_management', 'hr'],
    'data': [
        'security/ir.model.access.csv',

        'data/sequences.xml',
        'data/inspecteur_data.xml',
        'data/label_templates.xml', 
        
        'views/inspection_affaire_views.xml',
        'views/sous_affaire_views.xml',
        'views/sous_affaire_inspecteur_views.xml',
        'views/inspecteur_views.xml',
        'views/equipement_views.xml',
        'views/rapport_views.xml',
        'views/rapport_affaire_views.xml',
        'views/sale_order_views.xml',
        'views/menus.xml',
        
    ],
    'images': [
        'static/description/icon.png',
        'static/description/templates/iec.png',
        'static/description/templates/ienc.png',
        'static/description/templates/le.png',
        'static/description/templates/vcie.png',
        'static/description/templates/vgpa.png',
        'static/description/templates/vgpeis.png',
        'static/description/templates/vpge.png',
        'static/description/templates/vti.png',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}