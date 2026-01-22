from xaiforge.forge_safety.policy import PolicyRule, SafetyPolicy
from xaiforge.forge_safety.redaction import REDACTION_TOKEN, redact_payload


def test_redaction_scrubs_secrets_and_pii():
    payload = {
        "text": "Contact me at jane.doe@example.com with token sk-12345678901234567890",
        "nested": {"jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.signature"},
    }
    result = redact_payload(payload)
    assert REDACTION_TOKEN in result.payload["text"]
    assert REDACTION_TOKEN in result.payload["nested"]["jwt"]
    assert "email" in result.redactions
    assert "api_key" in result.redactions
    assert "jwt" in result.redactions


def test_policy_blocks_on_redacted_secrets():
    policy = SafetyPolicy(
        rules=[
            PolicyRule(
                name="block-secrets", action="block", tags=["secret"], contains=[REDACTION_TOKEN]
            )
        ]
    )
    try:
        policy.evaluate({"input": "sk-12345678901234567890"})
    except ValueError as exc:
        assert "block-secrets" in str(exc)
    else:
        raise AssertionError("Expected policy to block")


def test_policy_warns_on_pii():
    policy = SafetyPolicy(
        rules=[PolicyRule(name="warn-email", action="warn", tags=["pii"], contains=["@"])]
    )
    decision = policy.evaluate({"input": "hello@example.com"})
    assert decision.allowed is True
    assert decision.action == "warn"
