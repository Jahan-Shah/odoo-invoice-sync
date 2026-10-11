import hmac
import json

from odoo import http
from odoo.http import request


class InvoiceSyncController(http.Controller):

    @http.route("/invoice_sync/push", type="http", auth="public",
                methods=["POST"], csrf=False)
    def push(self, **kw):
        expected = request.env["ir.config_parameter"].sudo().get_param(
            "invoice_sync.api_key"
        )
        given = request.httprequest.headers.get("X-API-Key", "")
        if not expected or not hmac.compare_digest(expected, given):
            return request.make_json_response({"error": "unauthorized"}, status=401)
        try:
            rows = json.loads(request.httprequest.get_data(as_text=True))
        except ValueError:
            return request.make_json_response({"error": "invalid JSON"}, status=400)
        if isinstance(rows, dict):
            rows = [rows]
        result = request.env["sync.invoice"].sudo()._upsert_rows(rows)
        return request.make_json_response(result, status=200)
