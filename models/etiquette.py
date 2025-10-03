from odoo import models, fields, api
from odoo.exceptions import ValidationError
import unicodedata
import base64
from io import BytesIO
import qrcode

class InspectionEtiquette(models.Model):
    _name = 'kes_inspections.etiquette'
    _description = 'Étiquette unique générée'
    _order = 'code_etiquette'
    
    _sql_constraints = [
        ('code_etiquette_unique', 'unique(code_etiquette)', 'Le code étiquette doit être unique!')
    ]
    
    # 🔹 LIENS AVEC SOUS-AFFAIRE ET PRODUIT
    sous_affaire_id = fields.Many2one(
        'kes_inspections.sous_affaire',
        string='Sous-affaire',
        ondelete='cascade'
    )
    
    sous_affaire_produit_id = fields.Many2one(
        'kes_inspections.sous_affaire_produit',
        string='Produit sous-affaire',
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        related='sous_affaire_produit_id.product_id',
        store=True,
        readonly=True
    )
    
    # Champs existants
    name = fields.Char(string='Nom étiquette', compute='_compute_name', store=True)
    code_etiquette = fields.Char(string='Code étiquette unique', required=True, readonly=True)
    numero_etiquette = fields.Integer(string='Numéro dans la série', required=True)
    
    equipement_id = fields.Many2one('kes_inspections.equipement', string='Équipement', required=True, ondelete='cascade')
    date_generation = fields.Date(string='Date de génération', default=fields.Date.today, readonly=True)
    
    # Champs liés à l'équipement
    equipement_name = fields.Char(string='Nom équipement', related='equipement_id.name', readonly=True)

    @api.depends('equipement_name')
    def _compute_equipement_ascii(self):
        for rec in self:
            if rec.equipement_name:
                # Supprimer les accents
                rec.equipement_ascii = unicodedata.normalize('NFKD', rec.equipement_name).encode('ASCII', 'ignore').decode('utf-8')
            else:
                rec.equipement_ascii = ''

    equipement_ascii = fields.Char(string="Equipement ASCII", compute="_compute_equipement_ascii")

    equipement_type = fields.Selection(string='Type équipement', related='equipement_id.type_equipement', readonly=True)
    affaire_id = fields.Many2one(string='Affaire', related='equipement_id.affaire_id', readonly=True)
    
    # QR Code dynamique
    qr_code = fields.Binary(string='QR Code', compute='_generate_qr_code', store=True)
    qr_code_url = fields.Char(string='URL QR Code', compute='_generate_qr_code', store=True)

    # NOUVEAU : Champ spécifique pour le template PDF
    qr_code_pdf = fields.Char(string='QR Code PDF', compute='_compute_qr_code_pdf')

    @api.depends('qr_code')
    def _compute_qr_code_pdf(self):
        """Convertit le QR Code Binary en string pour le template PDF"""
        for etiquette in self:
            if etiquette.qr_code:
                # Conversion du Binary en string base64
                if isinstance(etiquette.qr_code, bytes):
                    etiquette.qr_code_pdf = etiquette.qr_code.decode('utf-8')
                else:
                    etiquette.qr_code_pdf = str(etiquette.qr_code)
            else:
                etiquette.qr_code_pdf = ''

    # Liens vers les rapports
    rapports_ids = fields.One2many('kes_inspections.rapport', 'etiquette_id', string='Rapports PDF')
    rapport_count = fields.Integer(string='Nombre de rapports', compute='_compute_rapport_count', store=True)

    # 🔹 CHAMPS TEMPORAIRES POUR L'UPLOAD
    rapport_temp = fields.Char(string="Champ technique", invisible=True)
    rapport_filename = fields.Char(string="Nom du fichier")
    rapport_file = fields.Binary(string="Fichier")
    

    # Type d'étiquette
    etiquette_modele = fields.Char(string="Modèle d'étiquette", compute='_compute_modele_etiquette', store=True)

    # Mapping des modèles d'étiquettes
    _MODELES_ETIQUETTES = {
        'inspection_electrique': "Étiquette Inspection Électrique (Nom + N° Armoire)",
        'inspection_thermographie': "Étiquette Thermographie (Quantité à générer)",
        'identification_local': "Étiquette Local Électrique (Nom + N° Local)",
        'ascenseur': "Étiquette Ascenseur (Quantité)",
        'verification_periodique': "Étiquette Vérification Périodique (N° Appareil + Quantité)",
        'verification_extincteur': "Étiquette Extincteur (N° Extincteur + Quantité)",
        'arc_flash': "Étiquette Arc Flash (Import Excel)",
        'plaque_identification': "Plaque Identification Extérieure (N° Extincteur + Quantité)"
    }

    # ─────────────────────────────────────────────────────────────
    # 🔸 MÉTHODES DE CALCUL
    # ─────────────────────────────────────────────────────────────
    
    @api.depends('rapports_ids')
    def _compute_rapport_count(self):
        for rec in self:
            rec.rapport_count = len(rec.rapports_ids)

    @api.depends('equipement_type')
    def _compute_modele_etiquette(self):
        for rec in self:
            rec.etiquette_modele = self._MODELES_ETIQUETTES.get(rec.equipement_type, "Modèle standard")

    @api.depends('code_etiquette')
    def _compute_name(self):
        for etiquette in self:
            etiquette.name = f"Étiquette {etiquette.code_etiquette or ''}"

    @api.depends('code_etiquette')
    def _generate_qr_code(self):
        """Génère le QR Code (image + URL)"""
        for etiquette in self:
            if etiquette.code_etiquette:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = f"{base_url}/inspection/etiquette/{etiquette.code_etiquette}"
                etiquette.qr_code_url = url

                # Génération QR code image
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4
                )
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")

                # ⚠️ Encodage en base64 côté Python
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                etiquette.qr_code = base64.b64encode(buffer.getvalue()).decode('utf-8')  # stocke le Base64 en string

            else:
                etiquette.qr_code = False
                etiquette.qr_code_url = False


    # ─────────────────────────────────────────────────────────────
    # 🔸 NOUVELLE MÉTHODE POUR UPLOAD
    # ─────────────────────────────────────────────────────────────
    
    def action_upload_rapport(self):
        """Upload un nouveau rapport pour cette étiquette"""
        self.ensure_one()
        
        if not self.rapport_filename or not self.rapport_file:
            raise ValidationError("Veuillez sélectionner un fichier et donner un nom.")
        
        # Vérifier l'extension du fichier
        filename_lower = self.rapport_filename.lower()
        if not (filename_lower.endswith('.pdf') or filename_lower.endswith('.doc') or filename_lower.endswith('.docx')):
            raise ValidationError("Seuls les fichiers PDF et Word sont acceptés.")
        
        # Déterminer le type de fichier
        file_type = 'pdf' if filename_lower.endswith('.pdf') else 'word'
        
        # Créer le rapport
        rapport_vals = {
            'name': f"Rapport - {self.code_etiquette}",
            'filename': self.rapport_filename,
            'file': self.rapport_file,
            'file_type': file_type,
            'etiquette_id': self.id,
            'sous_affaire_id': self.sous_affaire_id.id,
        }
        
        self.env['kes_inspections.rapport'].create(rapport_vals)
        
        # Réinitialiser les champs d'upload
        self.rapport_filename = False
        self.rapport_file = False
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Rapport uploadé',
                'message': f'Le rapport a été uploadé avec succès pour l\'étiquette {self.code_etiquette}',
                'sticky': False,
            }
        }

    @api.model
    def create(self, vals):
        if 'code_etiquette' in vals:
            existing = self.search([('code_etiquette', '=', vals['code_etiquette'])], limit=1)
            if existing:
                raise ValidationError(f"Le code étiquette {vals['code_etiquette']} existe déjà!")
        return super().create(vals)

    # ─────────────────────────────────────────────────────────────
    # 🔸 ACTIONS
    # ─────────────────────────────────────────────────────────────

    def action_voir_rapports(self):
        """Ouvre la vue liste des rapports liés à cette étiquette"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Rapports - {self.code_etiquette}',
            'res_model': 'kes_inspections.rapport',
            'view_mode': 'list,form,kanban',
            'domain': [('etiquette_id', '=', self.id)],
            'context': {
                'default_etiquette_id': self.id,
                'default_sous_affaire_id': self.sous_affaire_id.id if self.sous_affaire_id else False
            }
        }
    
    def print_etiquette(self):
        """Télécharger l'étiquette PDF correspondant au type d'équipement"""
        self.ensure_one()
        
        report_map = {
            'inspection_electrique': 'report_etiquette_inspection_electrique',
            'inspection_thermographie': 'report_etiquette_thermographie',
            'identification_local': 'report_etiquette_identification_local',
            'ascenseur': 'report_etiquette_ascenseur',
            'verification_periodique': 'report_etiquette_verification_periodique',
            'verification_extincteur': 'report_etiquette_verification_extincteur',
            'arc_flash': 'report_etiquette_arc_flash',
            'plaque_identification': 'report_etiquette_plaque_identification',
        }
        
        type_etiquette = self.equipement_type
        report_id = report_map.get(type_etiquette)
        
        if not report_id:
            raise ValidationError(f"Aucun rapport PDF défini pour le type : {type_etiquette}")
        
        # Construction de l'External ID complet
        report_external_id = f'kes_inspections.{report_id}'
        report = self.env.ref(report_external_id)

        # ✅ Version compatible Odoo 16+
        pdf_content, _ = report._render_qweb_pdf(report.id, res_ids=self.ids)

        pdf_base64 = base64.b64encode(pdf_content)
        
        attachment = self.env['ir.attachment'].create({
            'name': f'Etiquette_{self.code_etiquette}.pdf',
            'type': 'binary',
            'datas': pdf_base64,
            'res_model': 'kes_inspections.etiquette',
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


    def download_qr_code(self):
        """Télécharge le QR Code sous forme d'image PNG sans quitter la page"""
        self.ensure_one()
        
        if not self.qr_code:
            raise ValidationError("Aucun QR Code disponible pour cette étiquette.")
        
        # Créer un attachment temporaire
        filename = f"QRCode_{self.code_etiquette}.png"
        
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': self.qr_code,
            'res_model': 'kes_inspections.etiquette',
            'res_id': self.id,
            'mimetype': 'image/png'
        })
        
        # Retourner l'URL de téléchargement de l'attachment
        download_url = f'/web/content/{attachment.id}?download=true'
        
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'new',  # Ouvre dans un nouvel onglet/fenêtre
        }