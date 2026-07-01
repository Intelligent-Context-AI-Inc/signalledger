from __future__ import annotations

import hmac
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

from ecl_trainer.core.models import SignedLedgerEnvelope
from ecl_trainer.core.policy import NoPayloadValidator, sha256_hex
from ecl_trainer.core.serialization import canonical_json, canonical_sha256


class AbstractControlPlaneClient(ABC):
    @abstractmethod
    def register_dataset(self, metadata: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def log_training_checkpoint(self, checkpoint_id: str, exposed_dataset_hash: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def correlate_eval_outcome(self, checkpoint_id: str, metrics: dict) -> dict:
        raise NotImplementedError


@dataclass(frozen=True)
class SigningConfig:
    secret: str
    algorithm: str = "hmac-sha256"


class LedgerEnvelopeSigner:
    def __init__(self, config: SigningConfig) -> None:
        self.config = config

    def sign(self, payload: dict[str, Any]) -> str:
        message = canonical_json(payload).encode("utf-8")
        return hmac.new(self.config.secret.encode("utf-8"), message, "sha256").hexdigest()


class LicenseAuthorizationInterceptor:
    def __init__(self, mode: str = "community", license_token: str | None = None) -> None:
        if mode not in {"community", "saas", "vpc"}:
            raise ValueError("mode must be community, saas, or vpc")
        self.mode = mode
        self.license_token = license_token

    def validate(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "authorized": True,
            "time_bound_license_placeholder": self.license_token is not None,
            "encrypted_license_placeholder": self.mode in {"saas", "vpc"},
            "air_gapped_validation_placeholder": self.mode == "vpc",
        }


class SaaSControlPlaneClient(AbstractControlPlaneClient):
    def __init__(
        self,
        *,
        endpoint_url: str,
        tenant_id: str,
        project_namespace: str,
        api_key: str | None = None,
        timeout: float = 10.0,
        signing_config: SigningConfig | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.tenant_id = tenant_id
        self.project_namespace = project_namespace
        self.api_key = api_key or os.getenv("ECL_TRAINER_API_KEY")
        self.timeout = timeout
        self.signer = LedgerEnvelopeSigner(signing_config or SigningConfig(secret=self.api_key or "local-dev"))
        LicenseAuthorizationInterceptor(mode="saas", license_token=self.api_key).validate()

    def register_dataset(self, metadata: dict) -> dict:
        return self._submit("data_ingest", metadata)

    def log_training_checkpoint(self, checkpoint_id: str, exposed_dataset_hash: str) -> dict:
        return self._submit(
            "training_checkpoint",
            {"checkpoint_id": checkpoint_id, "exposed_dataset_hash": exposed_dataset_hash},
        )

    def correlate_eval_outcome(self, checkpoint_id: str, metrics: dict) -> dict:
        return self._submit("eval_outcome", {"checkpoint_id": checkpoint_id, "metrics_delta": metrics})

    def _envelope(self, event_type: str, payload: dict[str, Any]) -> SignedLedgerEnvelope:
        NoPayloadValidator().validate(payload)
        payload_hash = canonical_sha256(payload)
        envelope_payload = {
            "event_type": event_type,
            "payload_hash_sha256": payload_hash,
            "payload": payload,
            "project_namespace": self.project_namespace,
        }
        return SignedLedgerEnvelope(
            event_type=event_type,
            tenant_id_hash=sha256_hex(self.tenant_id),
            project_namespace=self.project_namespace,
            payload_hash_sha256=payload_hash,
            payload=payload,
            signature=self.signer.sign(envelope_payload),
        )

    def _submit(self, event_type: str, payload: dict[str, Any]) -> dict:
        envelope = self._envelope(event_type, payload)
        headers = {
            "content-type": "application/json",
            "idempotency-key": str(uuid4()),
        }
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.endpoint_url}/ledger/events",
                content=canonical_json(envelope),
                headers=headers,
            )
            response.raise_for_status()
            return response.json() if response.content else {"submitted": True}


class VPCControlPlaneClient(AbstractControlPlaneClient):
    def __init__(self, *, grpc_endpoint: str, project_namespace: str, license_token: str | None = None) -> None:
        self.grpc_endpoint = grpc_endpoint
        self.project_namespace = project_namespace
        self.license_token = license_token
        LicenseAuthorizationInterceptor(mode="vpc", license_token=license_token).validate()

    def register_dataset(self, metadata: dict) -> dict:
        NoPayloadValidator().validate(metadata)
        return self._local_stub("data_ingest", metadata)

    def log_training_checkpoint(self, checkpoint_id: str, exposed_dataset_hash: str) -> dict:
        payload = {"checkpoint_id": checkpoint_id, "exposed_dataset_hash": exposed_dataset_hash}
        NoPayloadValidator().validate(payload)
        return self._local_stub("training_checkpoint", payload)

    def correlate_eval_outcome(self, checkpoint_id: str, metrics: dict) -> dict:
        payload = {"checkpoint_id": checkpoint_id, "metrics_delta": metrics}
        NoPayloadValidator().validate(payload)
        return self._local_stub("eval_outcome", payload)

    def _local_stub(self, event_type: str, payload: dict[str, Any]) -> dict:
        return {
            "submitted": False,
            "transport": "vpc_grpc_placeholder",
            "grpc_endpoint_hash_sha256": sha256_hex(self.grpc_endpoint),
            "event_type": event_type,
            "payload_hash_sha256": canonical_sha256(payload),
            "local_attestation_placeholder": True,
        }
