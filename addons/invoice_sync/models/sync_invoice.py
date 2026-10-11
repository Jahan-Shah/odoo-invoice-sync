import logging

import requests

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SyncInvoice(models.Model):
    _name = "sync.invoice"
    _description = "Synced External Invoice"
    _inherit = ["mail.thread"]  # gives you the audit trail via tracking=True
    _order = "invoice_date desc"

    external_id = fields.Char(required=True, index=True, tracking=True)
    partner_name = fields.Char(required=True)
    amount = fields.Float(digits=(16, 2), tracking=True)
    ledger_amount = fields.Float(digits=(16, 2), tracking=True)
    invoice_date = fields.Date()
    recon_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("matched", "Matched"),
            ("mismatched", "Mismatched"),
            ("missing", "Missing in ledger"),
        ],
        default="pending",
        tracking=True,
    )

    # Integrity layer 1: enforced by PostgreSQL itself
    _sql_constraints = [
        ("external_id_unique", "unique(external_id)", "External ID must be unique."),
    ]

    # Integrity layer 2: business rules in Python
    @api.constrains("amount", "invoice_date")
    def _check_values(self):
        today = fields.Date.today()
        for rec in self:
            if rec.amount < 0:
                raise ValidationError("Amount cannot be negative.")
            if rec.invoice_date and rec.invoice_date > today:
                raise ValidationError("Invoice date cannot be in the future.")

    def action_reconcile(self):
        for rec in self:
            if not rec.ledger_amount:
                rec.recon_state = "missing"
            elif abs(rec.amount - rec.ledger_amount) < 0.01:
                rec.recon_state = "matched"
            else:
                rec.recon_state = "mismatched"
        return True

    def _upsert_rows(self, rows):
        created = updated = 0
        errors = []
        for row in rows:
            try:
                with self.env.cr.savepoint():
                    vals = {
                        "partner_name": row["client"],
                        "amount": row["amount"],
                        "ledger_amount": row.get("ledger_amount", 0),
                        "invoice_date": row["date"],
                    }
                    rec = self.search([("external_id", "=", str(row["id"]))], limit=1)
                    if rec:
                        rec.write(vals)
                        is_new = False
                    else:
                        rec = self.create({**vals, "external_id": str(row["id"])})
                        is_new = True
                    rec.action_reconcile()
                created += is_new
                updated += not is_new
            except Exception as exc:
                _logger.warning("Row skipped: %s", exc)
                rid = row.get("id") if isinstance(row, dict) else row
                errors.append(f"{rid}: {exc}")
        return {"created": created, "updated": updated, "errors": errors}

    @api.model
    def _cron_sync(self):
        params = self.env["ir.config_parameter"].sudo()
        url = params.get_param(
            "invoice_sync.api_url",
            "http://host.docker.internal:8000/invoices.json",
        )
        log = self.env["sync.log"].create({"source": url})
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            res = self._upsert_rows(resp.json())
            log.write({
                "status": "partial" if res["errors"] else "success",
                "created_count": res["created"],
                "updated_count": res["updated"],
                "error_count": len(res["errors"]),
                "error": "\n".join(res["errors"]) or False,
            })
        except Exception as exc:
            _logger.exception("Invoice sync failed")
            log.write({"status": "failed", "error": str(exc)})
