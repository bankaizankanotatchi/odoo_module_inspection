from odoo import models, fields, api
from odoo.exceptions import ValidationError

class InspectionRapport(models.Model):
    _name = 'kes_inspections.rapport'
    _description = "Rapport PDF lié à une étiquette / équipement"
    _order = 'create_date desc'

    name = fields.Char(string='Nom', required=False, default="Nouveau rapport")
    file = fields.Binary(string='Fichier', required=True)
    filename = fields.Char(string='Nom fichier', required=True)
    
    # 🔹 NOUVEAU : Support des fichiers Word et PDF
    file_type = fields.Selection([
        ('pdf', 'PDF'),
        ('word', 'Word'),
    ], string='Type de fichier', default='pdf', required=True)
    
    date_upload = fields.Date(string='Date d\'upload', default=fields.Date.context_today, readonly=True)
    
    # 🔹 LIEN AVEC SOUS-AFFAIRE
    sous_affaire_id = fields.Many2one('kes_inspections.sous_affaire', string='Sous-affaire', ondelete='cascade')
    
    # Liens existants (maintenus pour compatibilité)
    etiquette_id = fields.Many2one('kes_inspections.etiquette', string='Étiquette', ondelete='cascade', required=False)
    equipement_id = fields.Many2one('kes_inspections.equipement', string='Équipement', ondelete='set null')
    affaire_id = fields.Many2one('kes_inspections.affaire', string='Affaire', related='etiquette_id.affaire_id', store=True, readonly=True)
    type_equipement = fields.Selection(related='etiquette_id.equipement_type', string='Type équipement', readonly=True)

    _sql_constraints = [
        ('filename_unique_per_etiquette', 'unique(filename, etiquette_id)', 'Ce fichier existe déjà pour cette étiquette.')
    ]

    @api.model
    def create(self, vals):
        if 'filename' in vals and vals['filename']:
            fname = vals['filename'].lower()
            # 🔹 ACCEPTER PDF ET WORD
            if not (fname.endswith('.pdf') or fname.endswith('.doc') or fname.endswith('.docx')):
                raise ValidationError("Seuls les fichiers PDF et Word sont acceptés.")
            
            # Déterminer le type de fichier
            if fname.endswith('.pdf'):
                vals['file_type'] = 'pdf'
            else:
                vals['file_type'] = 'word'
                
        return super().create(vals)

    def action_download(self):
        """Retourne l'action de téléchargement"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/kes_inspections.rapport/{self.id}/file?download=true",
            'target': 'self',
        }