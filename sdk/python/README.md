# ensemble-protocol (Python SDK)

Reference implementation of the [Ensemble Protocol](../../SPEC.md).

## Install

```bash
pip install -e .
pip install -e ".[a2a]"   # A2A-relay binding
pip install -e ".[dev]"    # tests
```

## Usage

```python
from ensemble_protocol import Ensemble, Member, Role, CoordinationPattern, make_envelope
from ensemble_protocol.bindings.a2a_relay import A2ARelayBinding

ensemble = Ensemble.create(
    coordinator="financial-agent",
    namespace="bknight.dev",
    name="invoice-delivery-2026-06-25",
    members=[
        Member(agent_ref="document-agent", role=Role.SPECIALIST, skills=["document.ingest"]),
        Member(agent_ref="email-agent", role=Role.SPECIALIST, skills=["send_document"]),
    ],
)

binding = A2ARelayBinding(
    platform_url="http://localhost:8000",
    api_key="your-key",
    caller_agent_id="financial-agent",
)

replies = binding.broadcast(ensemble, "Deliver invoice #1042")
```

## Tests

```bash
pytest
```