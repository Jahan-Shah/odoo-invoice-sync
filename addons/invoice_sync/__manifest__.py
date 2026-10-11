{
    "name": "Invoice Sync & Reconciliation",
    "version": "18.0.1.0.0",
    "summary": "Sync external invoices, log every run, flag mismatches",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/sync_views.xml",
        "report/invoice_report.xml",
        "data/cron.xml",
    ],
    "application": True,
    "license": "LGPL-3",
}
