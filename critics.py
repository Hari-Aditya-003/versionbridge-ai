"""An advisory review cannot alter eligibility determined by policy and execution."""


def decision(verifier_passed, advice=None):
    return {
        "eligible": verifier_passed is True,
        "advisory": advice or {},
        "authority": "deterministic policy and executed checks",
        "human_decision": "pending maintainer review",
    }
