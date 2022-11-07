from odoo import fields, models, _, api
from odoo.exceptions import MissingError, UserError, ValidationError, AccessError



class League(models.Model):
    _name = 'x.league'
    _inherit = ['mail.thread']
    _order = 'start_date desc'

    name = fields.Char(string=_('Name'), required=True)
    match_ids = fields.One2many('x.match', 'league_id')
    law_id = fields.Many2one('x.league.type', required=True)
    type = fields.Selection([('solo', 'Solo'), ('dual', 'Dual')], required=True, default='solo')
    player_ids = fields.Many2many('x.player', 'x_player_x_league_rel', 'league_id', 'player_id', string=_('Players'))
    team_ids = fields.One2many('x.team', 'league_id', string=_('Teams'))
    fee_ids = fields.One2many('x.fee', 'league_id', required=True)
    total_fee = fields.Float(string=_('Total fee'), compute='compute_fee')
    start_date = fields.Date(string=_('Start date'), required=True)
    stop_date = fields.Date(string=_('End date'), required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('progress', 'In progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')],
        default='draft', copy=False)
    note = fields.Text(string=_('Note'))
    champion = fields.Char(string=_('The champion'))
    location = fields.Char(string=_('Location'))
    total_player = fields.Integer(string='Total player', compute='compute_player', tracking=True)
    participant_ids = fields.One2many('x.participants', 'league_id')
    total_match = fields.Integer(string=_('Total match'), compute='compute_match')

    def create_participant_ids(self):
        if self.type == 'solo':
            for record in self:
                vals = [(5, 0, 0)]
                for player in record.player_ids:
                    vals.append((0, 0, {'player_id': player.id}))
        else:
            for record in self:
                vals = [(5, 0, 0)]
                for team in record.team_ids:
                    vals.append((0, 0, {'team_id': team.id}))
        return vals

    @api.model
    def create(self, vals_list):
        res = super(League, self).create(vals_list)
        res.write({
            'participant_ids': res.create_participant_ids()
        })
        return res

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ['player_ids', 'team_ids']):
            for rec in self:
                rec.write({
                    'participant_ids': rec.create_participant_ids()
                })
        return res

    def compute_fee(self):
        for rec in self:
            rec.total_fee = 0
            fee = self.env['x.fee'].search([('league_id', '=', rec.id)])
            if fee:
                rec.total_fee = sum(x.fee_total for x in fee)

    def compute_match(self):
        for rec in self:
            rec.total_match = 0
            match = self.env['x.match'].search([('league_id', '=', rec.id)])
            if match:
                rec.total_match = len(match)

    def action_open_fee(self):
        self.ensure_one()
        self = self.sudo()
        action = self.env.ref('billiard_app.list_fee').read()[0]
        action['domain'] = [
            ('league_id', '=', self.id)
        ]
        action['context'] = {}
        return action

    def action_show_matches(self):
        self.ensure_one()
        self = self.sudo()
        action = self.env.ref('billiard_app.match_result').read()[0]
        action['domain'] = [
            ('league_id', '=', self.id)
        ]
        action['context'] = {}
        return action

    @api.depends('player_ids')
    def compute_player(self):
        for record in self:
            if record.type == 'solo':
                record.total_player = len(record.player_ids)
            else:
                record.total_player = len(record.team_ids)

    def cancel_league_button(self):
        self.state = 'cancelled'
        return {
            'type': 'ir.actions.act_url',
            'url': 'http://localhost:8014/web#cids=1&menu_id=143&action=164&model=x.league&view_type=list',
            'target': 'self'
        }

    def create_match(self, player, type):
        for record in self:
            # players = record.player_ids
            pair_player = [(a, b) for idx, a in enumerate(player) for b in player[idx + 1:]]
            for match in pair_player:
                self.env['x.match'].create({
                    'league_id': record.id,
                    'line_ids': [(0, 0, {'player_id': match[0].id}), (0, 0, {'player_id': match[1].id})] if type == 'solo' else [(0, 0, {'team_id': match[0].id}), (0, 0, {'team_id': match[1].id})]
                })

    def start_league_button(self):
        for record in self:
            record.state = 'progress'
            if not record.participant_ids:
                raise ValidationError(_('ghgjgj'))
            if record.type == 'solo':
                record.create_match(player=record.player_ids, type='solo')
            else:
                record.create_match(player=record.team_ids, type='dual')

    def end_league_button(self):
        self.state = 'completed'

    @api.onchange('champion')
    def onchange_status(self):
        if self.champion:
            self.state = 'completed'
