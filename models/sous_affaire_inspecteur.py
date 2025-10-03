from odoo import models, fields, api

class SousAffaireInspecteur(models.Model):
    _name = 'kes_inspections.sous_affaire_inspecteur'
    _description = 'Inspecteurs assignés à la sous-affaire'
    
    sous_affaire_id = fields.Many2one(
        'kes_inspections.sous_affaire', 
        string='Sous-affaire',
        required=True,
        ondelete='cascade'
    )
    
    inspecteur_id = fields.Many2one(
        'hr.employee', 
        string='Inspecteur',
        required=True,
        domain=[('department_id.name', '=', 'INSPECTION')]
    )
    
    role = fields.Selection([
        ('site', 'Site seulement'),
        ('rapport', 'Rapport seulement'), 
        ('site_rapport', 'Site et Rapport'),
    ], string='Rôle', required=True, default='site_rapport')
    
    # Informations liées pour affichage
    nom_complet = fields.Char(string='Nom', related='inspecteur_id.name', readonly=True)
    email = fields.Char(string='Email', related='inspecteur_id.work_email', readonly=True)
    telephone = fields.Char(string='Téléphone', related='inspecteur_id.mobile_phone', readonly=True)
    poste = fields.Char(string='Poste', related='inspecteur_id.job_id.name', readonly=True)

    _sql_constraints = [
        ('inspecteur_unique_per_sous_affaire', 
         'unique(sous_affaire_id, inspecteur_id)', 
         'Cet inspecteur est déjà assigné à cette sous-affaire.')
    ]