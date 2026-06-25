# Invoice delivery ensemble

Reference ensemble for the life-federation invoice flow:

1. **financial-agent** (coordinator) receives an invoice delivery request
2. **document-agent** ingests the PDF via `document.ingest`
3. **email-agent** sends the document via `send_document`
4. Coordinator polls `action_status` until delivery completes

## Coordination sequence

```
financial-agent                    document-agent          email-agent
      |                                  |                      |
      |-- broadcast: ingest PDF -------->|                      |
      |<--------- documentId ------------|                      |
      |-- unicast: send_document ------------------------------>|
      |<------------------------- taskId -----------------------|
      |-- unicast: action_status (poll) ----------------------->|
      |<------------------------- state -----------------------|
```

In ESP terms:

| Step | Pattern | Selector | Intent |
|------|---------|----------|--------|
| Ingest | `unicast` | `agent:document-agent` | `ingest_invoice_pdf` |
| Send | `unicast` | `skill:send_document` | `deliver_invoice` |
| Poll | `unicast` | `agent:email-agent` | `reconcile_delivery` |

## Example envelope (ingest step)

```json
{
  "esp_version": "0.1.0",
  "ensemble_id": "ens://bknight.dev/invoice-delivery-2026-06-25",
  "pattern": "unicast",
  "from": { "agent_ref": "financial-agent", "role": "coordinator" },
  "to": { "selector": "agent:document-agent" },
  "correlation_id": "msg-ingest-001",
  "payload": {
    "intent": "ingest_invoice_pdf",
    "a2a_message": {
      "role": "user",
      "parts": [{ "text": "Ingest invoice document inv-1042.pdf" }],
      "metadata": {
        "skillId": "document.ingest",
        "sourceRef": "invoice:1042",
        "name": "inv-1042.pdf",
        "mimeType": "application/pdf"
      }
    }
  },
  "metadata": {
    "idempotency_key": "inv-1042-ingest"
  }
}
```

See `ensemble.json` for the full membership manifest.