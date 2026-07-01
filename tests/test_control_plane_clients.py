import inspect

import pytest

from ecl_trainer.core.client import AbstractControlPlaneClient, SaaSControlPlaneClient, VPCControlPlaneClient
from ecl_trainer.core.exceptions import PayloadExfiltrationException


def test_control_plane_clients_share_interface():
    abstract_methods = {
        name: inspect.signature(getattr(AbstractControlPlaneClient, name))
        for name in ["register_dataset", "log_training_checkpoint", "correlate_eval_outcome"]
    }
    for client_type in [SaaSControlPlaneClient, VPCControlPlaneClient]:
        for name, signature in abstract_methods.items():
            assert inspect.signature(getattr(client_type, name)) == signature


def test_saas_client_validates_before_transport():
    client = SaaSControlPlaneClient(
        endpoint_url="https://ledger.invalid",
        tenant_id="tenant",
        project_namespace="project",
        api_key="key",
    )
    with pytest.raises(PayloadExfiltrationException):
        client.register_dataset({"prompt": "blocked"})


def test_vpc_client_returns_metadata_only_stub():
    client = VPCControlPlaneClient(grpc_endpoint="localhost:50051", project_namespace="project")
    result = client.log_training_checkpoint("ckpt", "hash")
    assert result["transport"] == "vpc_grpc_placeholder"
