"""A2A-relay binding — maps ESP patterns to pairwise A2A calls through an HTTP relay.

Expects a relay that exposes POST /a2a/{target_agent_id} and threads messages by
shared contextId (ensemble_id).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx

from ..ensemble import Ensemble
from ..models import Addressing, Envelope, Payload
from ..patterns import CoordinationPattern


class A2ARelayBinding:
    """Execute ESP coordination patterns via an HTTP A2A relay."""

    def __init__(
        self,
        *,
        platform_url: str,
        api_key: str,
        caller_agent_id: str,
        timeout: float = 60.0,
    ) -> None:
        self.platform_url = platform_url.rstrip("/")
        self.api_key = api_key
        self.caller_agent_id = caller_agent_id
        self.timeout = timeout

    def execute(
        self,
        ensemble: Ensemble,
        pattern: CoordinationPattern,
        text: str,
        *,
        to_selector: str | None = None,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Run a coordination pattern and return {agent_ref: reply_text}."""
        return asyncio.run(
            self.aexecute(
                ensemble,
                pattern,
                text,
                to_selector=to_selector,
                intent=intent,
                metadata=metadata,
            )
        )

    async def aexecute(
        self,
        ensemble: Ensemble,
        pattern: CoordinationPattern,
        text: str,
        *,
        to_selector: str | None = None,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        selector = to_selector or self._default_selector(pattern)
        envelope = ensemble.make_envelope(
            pattern,
            to=Addressing(selector=selector),
            payload=Payload(intent=intent or pattern.value, text=text),
            metadata=metadata,
        )
        return await self.asend_envelope(ensemble, envelope)

    def broadcast(
        self,
        ensemble: Ensemble,
        text: str,
        *,
        to_selector: str = "role:specialist",
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        return self.execute(
            ensemble,
            CoordinationPattern.BROADCAST,
            text,
            to_selector=to_selector,
            intent=intent,
            metadata=metadata,
        )

    def unicast(
        self,
        ensemble: Ensemble,
        target_agent: str,
        text: str,
        *,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        replies = self.execute(
            ensemble,
            CoordinationPattern.UNICAST,
            text,
            to_selector=f"agent:{target_agent}",
            intent=intent,
            metadata=metadata,
        )
        return replies[target_agent]

    async def asend_envelope(
        self,
        ensemble: Ensemble,
        envelope: Envelope,
    ) -> dict[str, str]:
        targets = ensemble.resolve_agent_refs(
            envelope.to.selector,
            exclude_self=envelope.from_.agent_ref,
        )
        if not targets:
            raise ValueError(f"no targets for selector {envelope.to.selector!r}")

        if envelope.pattern == CoordinationPattern.UNICAST and len(targets) != 1:
            raise ValueError(f"unicast requires exactly one target, got {len(targets)}")

        text = envelope.payload.text or ""
        if not text and envelope.payload.a2a_message:
            parts = envelope.payload.a2a_message.get("parts") or []
            text = " ".join(p.get("text", "") for p in parts if isinstance(p, dict))

        context_id = ensemble.ensemble_id

        if envelope.pattern == CoordinationPattern.REQUEST_ANY:
            return await self._request_any(targets, text, context_id, envelope)

        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        ) as client:
            results: dict[str, str] = {}
            for target in targets:
                results[target] = await self._acall(
                    client, target, text, context_id, envelope
                )
            return results

    async def _request_any(
        self,
        targets: list[str],
        text: str,
        context_id: str,
        envelope: Envelope,
    ) -> dict[str, str]:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        ) as client:
            tasks = {
                t: asyncio.create_task(self._acall(client, t, text, context_id, envelope))
                for t in targets
            }
            done, pending = await asyncio.wait(
                tasks.values(), return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            winner_task = next(iter(done))
            winner = next(agent for agent, task in tasks.items() if task is winner_task)
            return {winner: winner_task.result()}

    async def _acall(
        self,
        client: httpx.AsyncClient,
        target_id: str,
        text: str,
        context_id: str,
        envelope: Envelope,
    ) -> str:
        # Prefer full a2a-sdk client when available for streaming support.
        try:
            return await self._acall_sdk(client, target_id, text, context_id, envelope)
        except ImportError:
            return await self._acall_jsonrpc(client, target_id, text, context_id, envelope)

    async def _acall_sdk(
        self,
        client: httpx.AsyncClient,
        target_id: str,
        text: str,
        context_id: str,
        envelope: Envelope,
    ) -> str:
        from a2a.client import ClientConfig, ClientFactory
        from a2a.types import AgentCapabilities, AgentCard, AgentInterface, Message, Part, Role
        from a2a.types import SendMessageRequest, TransportProtocol

        relay_url = f"{self.platform_url}/a2a/{target_id}"
        card = AgentCard(
            name=target_id,
            version="0.0.1",
            capabilities=AgentCapabilities(streaming=True),
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            supported_interfaces=[
                AgentInterface(url=relay_url, protocol_binding=TransportProtocol.JSONRPC)
            ],
        )
        a2a_client = ClientFactory(
            ClientConfig(
                streaming=True,
                httpx_client=client,
                supported_protocol_bindings=[TransportProtocol.JSONRPC],
            )
        ).create(card)

        message = Message(
            message_id=uuid.uuid4().hex,
            role=Role.ROLE_USER,
            parts=[Part(text=text)],
            context_id=context_id,
        )
        if envelope.payload.a2a_message:
            meta = envelope.payload.a2a_message.get("metadata")
            if meta:
                message.metadata = meta

        request = SendMessageRequest(message=message)
        parts: list[str] = []
        async for resp in a2a_client.send_message(request):
            au = getattr(resp, "artifact_update", None)
            if au and au.artifact:
                parts.extend(p.text for p in au.artifact.parts if p.text)
            if getattr(resp, "task", None) and resp.task.artifacts:
                for art in resp.task.artifacts:
                    parts.extend(p.text for p in art.parts if p.text)
        await a2a_client.close()

        out: list[str] = []
        for p in parts:
            if not out or out[-1] != p:
                out.append(p)
        return "".join(out)

    async def _acall_jsonrpc(
        self,
        client: httpx.AsyncClient,
        target_id: str,
        text: str,
        context_id: str,
        envelope: Envelope,
    ) -> str:
        """Minimal JSON-RPC fallback when a2a-sdk is not installed."""
        url = f"{self.platform_url}/a2a/{target_id}"
        message: dict[str, Any] = {
            "role": "ROLE_USER",
            "messageId": uuid.uuid4().hex,
            "contextId": context_id,
            "parts": [{"text": text}],
        }
        if envelope.payload.a2a_message:
            if "metadata" in envelope.payload.a2a_message:
                message["metadata"] = envelope.payload.a2a_message["metadata"]
            if "parts" in envelope.payload.a2a_message:
                message["parts"] = envelope.payload.a2a_message["parts"]

        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/send",
            "params": {"message": message},
        }
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        return _extract_text(data)

    @staticmethod
    def _default_selector(pattern: CoordinationPattern) -> str:
        if pattern == CoordinationPattern.UNICAST:
            raise ValueError("unicast requires to_selector=agent:{id}")
        return "role:specialist"


def _extract_text(obj: Any) -> str:
    """Depth-first search for text content in an A2A response."""
    if isinstance(obj, dict):
        if isinstance(obj.get("text"), str):
            return obj["text"]
        for value in obj.values():
            found = _extract_text(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _extract_text(item)
            if found:
                return found
    return ""