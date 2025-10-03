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
        
        'views/inspection_affaire_views.xml',
        'views/sous_affaire_views.xml',
        'views/sous_affaire_inspecteur_views.xml',
        'views/inspecteur_views.xml',
        'views/equipement_views.xml',
        'views/rapport_views.xml',
        'views/rapport_affaire_views.xml',
        'views/sale_order_views.xml',
        'views/menus.xml',
        
        'report/report_actions.xml',
        'report/report_etiquette_inspection_electrique_template.xml',
        'report/report_etiquette_thermographie_template.xml',
        'report/report_etiquette_identification_local_template.xml',
        'report/report_etiquette_ascenseur_template.xml',
        'report/report_etiquette_verification_periodique_template.xml',
        'report/report_etiquette_verification_extincteur_template.xml',
        'report/report_etiquette_arc_flash_template.xml',
        'report/report_etiquette_plaque_identification_template.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}