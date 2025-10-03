from odoo import models, fields, api

class InspectionInspecteur(models.Model):
    _name = 'kes_inspections.inspecteur'
    _description = 'Inspecteur pour les inspections'

    description = fields.Text(string="Description/Mission")

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employé",
        domain=[('department_id.name', '=', 'INSPECTION')],
        required=True
    )

    # Infos liées
    photo = fields.Binary(related='employee_id.image_1920', string="Photo", readonly=True)
    nom_complet = fields.Char(related='employee_id.name', string="Nom complet", readonly=True)
    email = fields.Char(related='employee_id.work_email', string="Email", readonly=True)
    poste = fields.Char(related='employee_id.job_id.name', string="Poste", readonly=True)
    telephone = fields.Char(related='employee_id.mobile_phone', string="Téléphone", readonly=True)

    disponibilite = fields.Selection([
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('absent', 'Absent'),
    ], string="Disponibilité", compute='_compute_disponibilite', store=True)

    affaire_ids = fields.Many2many('kes_inspections.affaire', string='Affaires assignées')
    
    # 🔹 NOUVEAU : PLANNING DES SOUS-AFFAIRES
    planning_sous_affaire_ids = fields.Many2many(
        'kes_inspections.sous_affaire',
        string='Sous-affaires en cours',
        compute='_compute_planning_sous_affaires'
    )
    
    planning_count = fields.Integer(
        string='Nombre de missions',
        compute='_compute_planning_count'
    )

    @api.depends('employee_id', 'affaire_ids.state', 'employee_id.active')
    def _compute_disponibilite(self):
        for rec in self:
            if not rec.employee_id or not rec.employee_id.active:
                rec.disponibilite = 'absent'
            elif rec.affaire_ids.filtered(lambda a: a.state in ('draft', 'in_progress')):
                rec.disponibilite = 'occupe'
            else:
                rec.disponibilite = 'disponible'

    @api.depends('employee_id')
    def _compute_planning_sous_affaires(self):
        """Calcule les sous-affaires où l'inspecteur est assigné"""
        for inspecteur in self:
            if inspecteur.employee_id:
                # Récupérer toutes les sous-affaires où cet employé est inspecteur
                sous_affaires = self.env['kes_inspections.sous_affaire_inspecteur'].search([
                    ('inspecteur_id', '=', inspecteur.employee_id.id)
                ]).mapped('sous_affaire_id')
                inspecteur.planning_sous_affaire_ids = [(6, 0, sous_affaires.ids)]
            else:
                inspecteur.planning_sous_affaire_ids = [(5, 0, 0)]

    @api.depends('planning_sous_affaire_ids')
    def _compute_planning_count(self):
        for inspecteur in self:
            inspecteur.planning_count = len(inspecteur.planning_sous_affaire_ids)

    def name_get(self):
        """Afficher le nom complet au lieu de l'ID"""
        result = []
        for rec in self:
            name = rec.nom_complet or rec.employee_id.name or f"Inspecteur {rec.id}"
            result.append((rec.id, name))
        return result
    
    @api.model
    def init_inspecteurs(self):
        """Méthode pour initialiser les inspecteurs automatiquement"""
        employees = self.env['hr.employee'].search([('department_id.name', '=', 'INSPECTION')])
        
        for emp in employees:
            # Vérifie qu'il n'existe pas déjà
            if not self.search([('employee_id', '=', emp.id)]):
                self.create({'employee_id': emp.id})

    # 🔹 NOUVELLE ACTION POUR VOIR LE PLANNING
    def action_voir_planning(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Planning - {self.nom_complet}',
            'res_model': 'kes_inspections.sous_affaire',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', self.planning_sous_affaire_ids.ids)],
            'context': {'create': False}
        }