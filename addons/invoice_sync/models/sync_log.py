from odoo import fields, models


class SyncLog(models.Model):
    _name = "sync.log"
    _description = "Invoice Sync Run Log"
    _order = "run_date desc"

    run_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    source = fields.Char(readonly=True)
    status = fields.Selection(
        [("running", "Running"), ("success", "Success"), ("partial", "Partial"), ("failed", "Failed")],
        default="running",
    )
    created_count = fields.Integer()
    updated_count = fields.Integer()
    error_count = fields.Integer()
    error = fields.Text()
