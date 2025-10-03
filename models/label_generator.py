import base64
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
import qrcode
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class LabelGenerator(models.Model):
    _name = 'label.generator'
    _description = 'Générateur d\'étiquettes'
    _rec_name = 'name'

    name = fields.Char('Nom de la génération', readonly=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('generated', 'Généré'),
        ('downloaded', 'Téléchargé')
    ], default='draft', string='État')
    
    # Sélection des enregistrements
    partner_id = fields.Many2one('res.partner', string='Client', required=True)
    product_id = fields.Many2one('product.product', string='Produit', required=True)
    
    label_count = fields.Integer('Nombre d\'étiquettes', required=True, default=1)
    next_label_number = fields.Integer('Prochain numéro', default=1)
    zip_file = fields.Binary('Fichier ZIP', readonly=True)
    zip_filename = fields.Char('Nom du fichier ZIP', readonly=True)
    
    generation_date = fields.Datetime('Date de génération', readonly=True)
    
    @api.model
    def _get_default_font(self):
        """Retourne une police par défaut"""
        try:
            return ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 12)
        except:
            return ImageFont.load_default()
    
    def generate_qr_code(self, data, size=100):
        """Génère un QR code"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
        return qr_img
    
    def _generate_unique_label_number(self, partner, product, sequence):
        """Génère un numéro unique pour l'étiquette"""
        # Format: PXXXXX-PYYYYY-NNNN
        # P = Partner ID, P = Product ID, N = Sequence
        return f"P{partner.id:05d}-P{product.id:05d}-{sequence:04d}"
    
    def create_label(self, template, partner, product, label_number, unique_code):
        """Crée une étiquette pour un client et produit donné"""
        if not template.template_image:
            raise UserError(_("Le modèle d'étiquette n'a pas d'image de base."))
        
        # Charger l'image de base et conserver sa taille d'origine
        template_data = base64.b64decode(template.template_image)
        base_img = Image.open(io.BytesIO(template_data))
        
        # Conserver le mode original de l'image (RGB, RGBA, etc.)
        # Convertir en RGBA seulement si nécessaire pour la transparence
        if base_img.mode not in ('RGB', 'RGBA'):
            base_img = base_img.convert('RGBA')
        
        # Stocker la taille d'origine
        original_size = base_img.size
        
        # Créer le QR code avec le code unique
        qr_data = f"{unique_code}\nClient: {partner.name}\nProduit: {product.name}\nN°: {label_number}"
        
        qr_img = self.generate_qr_code(qr_data, template.qr_size)
        
        # Coller le QR code sur l'image (sans modifier la taille de base)
        if base_img.mode == 'RGBA':
            base_img.paste(qr_img, (template.qr_position_x, template.qr_position_y), qr_img)
        else:
            base_img.paste(qr_img, (template.qr_position_x, template.qr_position_y))
        
        # Ajouter le texte
        draw = ImageDraw.Draw(base_img)
        font = self._get_default_font()
        
        # Code unique
        draw.text(
            (template.client_number_x, template.client_number_y),
            unique_code,
            fill=template.font_color,
            font=font
        )
        
        # Nom client
        client_text = f"{partner.name[:20]}"
        draw.text(
            (template.client_name_x, template.client_name_y),
            client_text,
            fill=template.font_color,
            font=font
        )
        
        # Nom du produit (si espace disponible)
        if hasattr(template, 'product_name_x') and hasattr(template, 'product_name_y'):
            product_text = f"{product.name[:25]}"
            draw.text(
                (template.product_name_x, template.product_name_y),
                product_text,
                fill=template.font_color,
                font=font
            )
        
        # Vérifier que la taille n'a pas changé
        if base_img.size != original_size:
            base_img = base_img.resize(original_size, Image.Resampling.LANCZOS)
        
        return base_img
    
    def action_generate_labels(self):
        """Génère toutes les étiquettes avec des numéros uniques"""
        if not self.partner_id:
            raise UserError(_("Veuillez sélectionner un client."))
        
        if not self.product_id:
            raise UserError(_("Veuillez sélectionner un produit."))
        
        if self.label_count < 1:
            raise UserError(_("Le nombre d'étiquettes doit être au moins 1."))
        
        labels = []
        label_template_model = self.env['label.template']
        
        # Récupérer le template pour le produit
        template = label_template_model.get_template_for_product(self.product_id.id)
        
        if not template:
            raise UserError(_(f"Aucun modèle d'étiquette trouvé pour le produit {self.product_id.name}."))
        
        # Générer les étiquettes avec des numéros uniques
        for i in range(self.label_count):
            sequence_number = self.next_label_number + i
            unique_code = self._generate_unique_label_number(
                self.partner_id, 
                self.product_id, 
                sequence_number
            )
            
            label_img = self.create_label(
                template, 
                self.partner_id, 
                self.product_id,
                sequence_number,
                unique_code
            )
            
            filename = f"label_{unique_code}.png"
            labels.append((filename, label_img, unique_code))
        
        if not labels:
            raise UserError(_("Aucune étiquette n'a pu être générée."))
        
        # Créer le fichier ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, img, unique_code in labels:
                img_buffer = io.BytesIO()
                # Sauvegarder avec le format d'origine si possible
                img.save(img_buffer, format='PNG', optimize=False)
                img_buffer.seek(0)
                zip_file.writestr(filename, img_buffer.getvalue())
        
        zip_buffer.seek(0)
        zip_data = base64.b64encode(zip_buffer.getvalue())

        generation_name = f"Etiquettes_{self.partner_id.name}_{self.product_id.name}"

        # Mettre à jour l'enregistrement
        self.write({
            'name': generation_name,
            'state': 'generated',
            'zip_file': zip_data,
            'zip_filename': f"etiquettes_{generation_name.replace(' ', '_')}.zip",
            'generation_date': fields.Datetime.now(),
            'next_label_number': self.next_label_number + self.label_count
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'label.generator',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_download_labels(self):
        """Télécharge le fichier ZIP des étiquettes"""
        if not self.zip_file:
            raise UserError(_("Aucun fichier à télécharger. Générez d'abord les étiquettes."))
        
        self.state = 'downloaded'
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/label.generator/{self.id}/zip_file/{self.zip_filename}?download=true',
            'target': 'self',
        }