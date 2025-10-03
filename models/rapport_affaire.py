from odoo import models, fields, api
from odoo.exceptions import ValidationError

class InspectionRapportAffaire(models.Model):
    _name = 'kes_inspections.rapport.affaire'
    _description = "Rapport PDF lié directement à une affaire"
    _order = 'create_date desc'

    name = fields.Char(string='Nom rapport', required=True, default="Nouveau rapport")
    file = fields.Binary(string='Fichier PDF', required=True)
    filename = fields.Char(string='Nom fichier', required=True)
    date_upload = fields.Date(string='Date d\'upload', default=fields.Date.context_today, readonly=True)
    affaire_id = fields.Many2one('kes_inspections.affaire', string='Affaire', ondelete='cascade', required=True)
    
    # 🔹 NOUVEAU : Support des fichiers Word et PDF
    file_type = fields.Selection([
        ('pdf', 'PDF'),
        ('word', 'Word'),
    ], string='Type de fichier', default='pdf', required=True)
    
    qrcode_affaire = fields.Binary(related='affaire_id.qrcode_affaire', string='QR Code Affaire', readonly=True)

    _sql_constraints = [
        ('filename_unique_per_affaire', 'unique(filename, affaire_id)', 'Ce fichier existe déjà pour cette affaire.')
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
            'url': f"/web/content/kes_inspections.rapport.affaire/{self.id}/file?download=true",
            'target': 'self',
        }