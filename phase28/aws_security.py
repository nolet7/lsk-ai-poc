"""P28-10: offline-verifiable Bedrock role policy and runtime-client boundary.

Creating a client is NOT permission to invoke inference. Never pass this client
straight to an unbudgeted code path. IAM/VPC restrictions are independently
validated in the target AWS account before deployment.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from phase28.config import AISettings

_REGION = re.compile(r"^(?:us|eu|ap|sa|ca|me|af|il)-(?:[a-z]+-)+[1-9][0-9]*$")
_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]{0,255}$")
_VPCE = re.compile(r"^vpce-[0-9a-f]{8,17}$")


class RuntimeApprovalRequired(RuntimeError):
    """Runtime construction has not been authorized."""


@dataclass(frozen=True, slots=True)
class RuntimeApproval:
    """Explicit startup control, not a substitute for authenticated IAM.

    This should be issued by trusted operator configuration, NEVER request data.
    """
    approved: bool = False
    expected_region: str = ""
    expected_model_id: str = ""


def foundation_model_arn(region: str, model_id: str) -> str:
    """Only regional foundation-model IDs; profiles require different policies."""
    if not isinstance(region, str) or not _REGION.fullmatch(region):
        raise ValueError("Invalid region")
    if not isinstance(model_id, str) or not _MODEL.fullmatch(model_id):
        raise ValueError("Only a foundation-model ID is supported")
    return f"arn:aws:bedrock:{region}::foundation-model/{model_id}"


def build_invoke_policy(*, region: str, model_id: str, vpce_id: str) -> dict:
    """Least-privilege identity policy for single-region non-streaming Converse.

    Explicit SourceVpce is required, so a stolen role credential cannot use
    this identity permission outside the approved endpoint. Other attached IAM
    permissions, endpoint policies, SCPs, and resource controls still matter.
    """
    resource = foundation_model_arn(region, model_id)
    if not isinstance(vpce_id, str) or not _VPCE.fullmatch(vpce_id):
        raise ValueError("A concrete approved VPC endpoint ID is required")
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowConverseForOneModelViaApprovedEndpoint",
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel"],
                "Resource": [resource],
                "Condition": {"StringEquals": {"aws:SourceVpce": vpce_id}},
            }
        ],
    }


def create_runtime_client(
    settings: AISettings,
    *,
    approval: RuntimeApproval | None = None,
    client_factory: Callable[..., Any] | None = None,
    config_factory: Callable[..., Any] | None = None,
) -> Any:
    """Construct a client through injected SDK factories, without invoking AWS.

    No boto3 import or SDK credential acquisition is done by this module.
    The production composition root must supply a verified SDK session and
    approved role; this function does NOT make the runtime safe for live calls.
    SDK retries are disabled to avoid double inference charges on ambiguity.
    """
    if not isinstance(settings, AISettings):
        raise TypeError("settings must be AISettings")
    if not (settings.live_inference and settings.live_inference_ack):
        raise RuntimeApprovalRequired("Live inference configuration is disabled")
    if (
        not isinstance(approval, RuntimeApproval)
        or approval.approved is not True
        or approval.expected_region != settings.aws_region
        or approval.expected_model_id != settings.model_id
    ):
        raise RuntimeApprovalRequired("Trusted runtime approval is required")
    foundation_model_arn(settings.aws_region, settings.model_id)
    if not callable(client_factory) or not callable(config_factory):
        raise RuntimeApprovalRequired("Trusted, injected SDK factories are required")
    sdk_config = config_factory(
        connect_timeout=min(5, settings.timeout_seconds),
        read_timeout=settings.timeout_seconds,
        retries={"mode": "standard", "total_max_attempts": 1},
    )
    return client_factory(
        "bedrock-runtime", region_name=settings.aws_region, config=sdk_config
    )
