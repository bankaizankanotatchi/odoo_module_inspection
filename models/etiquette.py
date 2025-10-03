from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
from io import BytesIO
import qrcode
import zipfile

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class InspectionEtiquette(models.Model):
    _name = 'kes_inspections.etiquette'
    _description = 'Étiquette unique générée'
    _order = 'code_etiquette'
    
    _sql_constraints = [
        ('code_etiquette_unique', 'unique(code_etiquette)', 'Le code étiquette doit être unique!')
    ]
    
    # Champs existants
    name = fields.Char(string='Nom étiquette', compute='_compute_name', store=True)
    code_etiquette = fields.Char(string='Code étiquette unique', required=True, readonly=True)
    numero_etiquette = fields.Integer(string='Numéro dans la série', required=True)
    
    sous_affaire_id = fields.Many2one('kes_inspections.sous_affaire', string='Sous-affaire', required=True, ondelete='cascade')
    
    # 🔥 AJOUTER CE CHAMP MANQUANT
    affaire_id = fields.Many2one(
        'kes_inspections.affaire',
        string='Affaire',
        related='sous_affaire_id.affaire_id',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Client',
        compute='_compute_partner_id',
        store=True,
        readonly=True
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
    
    equipement_id = fields.Many2one('kes_inspections.equipement', string='Équipement', required=True, ondelete='cascade')
    equipement_name = fields.Char(string='Nom équipement', related='equipement_id.name', readonly=True)
    equipement_type = fields.Selection(string='Type équipement', related='equipement_id.type_equipement', readonly=True)
    
    date_generation = fields.Date(string='Date de génération', default=fields.Date.today, readonly=True)
    
    # Template associé automatiquement
    label_template_id = fields.Many2one('label.template', string='Modèle', compute='_compute_label_template', store=True)

        # Liens vers les rapports
    rapports_ids = fields.One2many('kes_inspections.rapport', 'etiquette_id', string='Rapports PDF')
    rapport_count = fields.Integer(string='Nombre de rapports', compute='_compute_rapport_count', store=True)

    # 🔹 CHAMPS TEMPORAIRES POUR L'UPLOAD
    rapport_temp = fields.Char(string="Champ technique", invisible=True)
    rapport_filename = fields.Char(string="Nom du fichier")
    rapport_file = fields.Binary(string="Fichier")
    
    # QR Code
    qr_code = fields.Binary(string='QR Code', compute='_generate_qr_code', store=True)
    qr_code_url = fields.Char(string='URL QR Code', compute='_generate_qr_code', store=True)
    
    # Mapping des templates
    _MAPPING_EQUIPEMENT_TEMPLATE = {
        'inspection_electrique': 'label_template_iec',
        'inspection_thermographie': 'label_template_vti', 
        'identification_local': 'label_template_le',
        'ascenseur': 'label_template_vgpa',
        'verification_periodique': 'label_template_vpge',
        'verification_extincteur': 'label_template_ienc',
        'arc_flash': 'label_template_vcie',
        'plaque_identification': 'label_template_vgpeis'
    }

    @api.depends('sous_affaire_id')
    def _compute_partner_id(self):
        """Calcule le partner_id depuis la sous-affaire"""
        for rec in self:
            if rec.sous_affaire_id and hasattr(rec.sous_affaire_id, 'partner_id'):
                rec.partner_id = rec.sous_affaire_id.partner_id
            else:
                rec.partner_id = False

    @api.depends('equipement_type')
    def _compute_label_template(self):
        """Assigne automatiquement le template basé sur le type d'équipement"""
        for rec in self:
            template_xml_id = self._MAPPING_EQUIPEMENT_TEMPLATE.get(rec.equipement_type)
            if template_xml_id:
                template = self.env.ref(f'kes_inspections.{template_xml_id}', raise_if_not_found=False)
                rec.label_template_id = template
            else:
                rec.label_template_id = False

    @api.depends('code_etiquette')
    def _compute_name(self):
        for etiquette in self:
            etiquette.name = f"Étiquette {etiquette.code_etiquette or ''}"

    @api.depends('code_etiquette')
    def _generate_qr_code(self):
        """Génère le QR Code"""
        for etiquette in self:
            if etiquette.code_etiquette:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = f"{base_url}/inspection/etiquette/{etiquette.code_etiquette}"
                etiquette.qr_code_url = url

                qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")

                buffer = BytesIO()
                img.save(buffer, format="PNG")
                etiquette.qr_code = base64.b64encode(buffer.getvalue())
            else:
                etiquette.qr_code = False
                etiquette.qr_code_url = False

    def _get_default_font(self, size=12, bold=False):
        """Retourne une police par défaut, optionnellement en gras"""
        try:
            if bold:
                # Essayer d'abord une police en gras
                try:
                    return ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", size)
                except:
                    # Fallback : utiliser la police normale en augmentant la taille pour simuler le gras
                    return ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", int(size * 1.1))
            else:
                return ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", size)
        except:
            try:
                return ImageFont.load_default()
            except:
                return None
            
    def generate_etiquette_image(self):
        """Génère l'image de l'étiquette avec le template"""
        self.ensure_one()
        
        if not self.label_template_id:
            raise ValidationError("Aucun modèle d'étiquette associé.")
        
        if not self.label_template_id.template_image:
            raise ValidationError("Le modèle d'étiquette n'a pas d'image de base.")
        
        if not PIL_AVAILABLE:
            raise ValidationError("La bibliothèque PIL/Pillow n'est pas installée.")
        
        try:
            # Charger l'image template
            template_data = base64.b64decode(self.label_template_id.template_image)
            base_img = Image.open(BytesIO(template_data))
            
            if base_img.mode not in ('RGB', 'RGBA'):
                base_img = base_img.convert('RGBA')
            
            original_size = base_img.size
            
            # Générer QR code
            partner_name = self.partner_id.name if self.partner_id else "Client non défini"
            product_name = self.product_id.name if self.product_id else "N/A"
            qr_data = f"{self.code_etiquette}\nClient: {partner_name}\nProduit: {product_name}"
            
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((self.label_template_id.qr_size, self.label_template_id.qr_size), Image.Resampling.LANCZOS)
            
            # Coller QR code
            if base_img.mode == 'RGBA':
                base_img.paste(qr_img, (self.label_template_id.qr_position_x, self.label_template_id.qr_position_y), qr_img)
            else:
                base_img.paste(qr_img, (self.label_template_id.qr_position_x, self.label_template_id.qr_position_y))
            
            # Ajouter texte
            draw = ImageDraw.Draw(base_img)
            font = self._get_default_font(self.label_template_id.font_size)
            
            # 🔥 SUPPRIMÉ : Ancien bloc pour le code étiquette
            # if self.label_template_id.client_number_x and self.label_template_id.client_number_y:
            #     draw.text(
            #         (self.label_template_id.client_number_x, self.label_template_id.client_number_y),
            #         self.code_etiquette,
            #         fill=self.label_template_id.font_color,
            #         font=font
            #     )
            
            # 🔥 NOUVEAU : Format client/lieu_intervention/numero_etiquette
            if self.label_template_id.client_name_x and self.label_template_id.client_name_y:
                # Récupérer le nom du client
                client_name = self.partner_id.name if self.partner_id else "Client"
                
                # Récupérer le lieu d'intervention depuis l'affaire principale
                lieu_intervention = ""
                if self.affaire_id and self.affaire_id.lieu_intervention:
                    lieu_intervention = self.affaire_id.lieu_intervention
                elif self.affaire_id and self.affaire_id.site_intervention:
                    lieu_intervention = self.affaire_id.site_intervention
                else:
                    lieu_intervention = "Lieu"
                
                # Limiter à 8 caractères maximum pour chaque partie
                if len(client_name) > 8:
                    client_formatted = client_name[:8]
                else:
                    client_formatted = client_name
                
                if len(lieu_intervention) > 8:
                    lieu_formatted = lieu_intervention[:8]
                else:
                    lieu_formatted = lieu_intervention
                
                # 🔥 FORMAT : client/lieu/numero
                client_text = f"{client_formatted}/{lieu_formatted}/{self.numero_etiquette}"
                
                draw.text(
                    (self.label_template_id.client_name_x, self.label_template_id.client_name_y),
                    client_text,
                    fill=self.label_template_id.font_color,
                    font=font
                )
            
            # Redimensionner si nécessaire
            if base_img.size != original_size:
                base_img = base_img.resize(original_size, Image.Resampling.LANCZOS)
            
            return base_img
            
        except Exception as e:
            raise ValidationError(f"Erreur lors de la génération d'image: {str(e)}")
        
    def action_generate_zip_etiquettes(self):
        """Génère un ZIP avec toutes les étiquettes sélectionnées"""
        if not self:
            raise ValidationError("Aucune étiquette sélectionnée.")
        
        zip_buffer = BytesIO()
        
        # 🔥 CORRECTION : Nom du ZIP basé sur la référence de la sous-affaire SANS créer de dossiers
        if len(self) == 1:
            # Une seule étiquette : nom basé sur la sous-affaire
            sous_affaire_ref = self.sous_affaire_id.name or "etiquettes"
            zip_folder_name = sous_affaire_ref.replace('/', '_').replace('\\', '_')  # 🔥 Supprimer les slashes
        else:
            # Plusieurs étiquettes : chercher une sous-affaire commune
            sous_affaires = self.mapped('sous_affaire_id')
            if len(sous_affaires) == 1:
                sous_affaire_ref = sous_affaires.name
                zip_folder_name = sous_affaire_ref.replace('/', '_').replace('\\', '_')  # 🔥 Supprimer les slashes
            else:
                # Étiquettes de différentes sous-affaires : nom générique
                zip_folder_name = f"etiquettes_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for etiquette in self:
                try:
                    # Générer l'image
                    etiquette_image = etiquette.generate_etiquette_image()
                    
                    # Convertir en bytes
                    img_buffer = BytesIO()
                    etiquette_image.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    
                    # 🔥 CORRECTION : Nom de fichier SIMPLE sans chemin
                    filename = f"etiquette_{etiquette.code_etiquette}.png"
                    zip_file.writestr(filename, img_buffer.getvalue())
                    
                except Exception as e:
                    raise ValidationError(f"Erreur avec l'étiquette {etiquette.code_etiquette}: {str(e)}")
        
        zip_buffer.seek(0)
        zip_data = base64.b64encode(zip_buffer.getvalue())
        
        # 🔥 CORRECTION : Nom du fichier ZIP propre
        zip_filename = f"{zip_folder_name}.zip"
        
        # Créer attachment pour téléchargement
        attachment = self.env['ir.attachment'].create({
            'name': zip_filename,
            'type': 'binary',
            'datas': zip_data,
            'res_model': 'kes_inspections.etiquette',
            'mimetype': 'application/zip'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    @api.model
    def create(self, vals):
        if 'code_etiquette' in vals:
            existing = self.search([('code_etiquette', '=', vals['code_etiquette'])], limit=1)
            if existing:
                raise ValidationError(f"Le code étiquette {vals['code_etiquette']} existe déjà!")
        return super().create(vals)
    


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