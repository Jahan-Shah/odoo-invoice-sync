"""Talk to Odoo from outside via the external XML-RPC API.

Credentials come from environment variables so nothing secret is committed:
    export ODOO_USER="you@example.com"
    export ODOO_API_KEY="<API key from Preferences -> Account Security>"
    python3 scripts/rpc_client.py
"""
import os
import time
import xmlrpc.client

URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DB = os.environ.get("ODOO_DB", "odoo_dev")
try:
    USER = os.environ["ODOO_USER"]
    PASSWORD = os.environ["ODOO_API_KEY"]
except KeyError as missing:
    raise SystemExit(f"Set the {missing} environment variable first.")

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PASSWORD, {})
if not uid:
    raise SystemExit("Authentication failed: check ODOO_DB, ODOO_USER and ODOO_API_KEY")
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def call(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, PASSWORD, model, method, list(args), kwargs)


# 1. aggregate report data, grouped in SQL
for r in call("sync.invoice", "read_group", [], ["amount:sum"], ["recon_state"], lazy=False):
    print(r["recon_state"], r["__count"], r["amount"])

# 2. create a record through the external API
ext_id = f"rpc-{int(time.time())}"
payload = {
    "external_id": ext_id, "partner_name": "RPC Client",
    "amount": 750.0, "ledger_amount": 750.0, "invoice_date": "2026-10-02",
}
new_id = call("sync.invoice", "create", payload)
call("sync.invoice", "action_reconcile", [new_id])
print(call("sync.invoice", "read", [new_id], fields=["external_id", "recon_state"]))

# 3. prove the integrity layer also holds from outside: reuse the same external_id
try:
    call("sync.invoice", "create", {**payload, "partner_name": "Dup", "amount": 1.0})
except xmlrpc.client.Fault as f:
    print("Rejected:", f.faultString.strip().splitlines()[-1])
