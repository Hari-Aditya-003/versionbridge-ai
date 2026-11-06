"""Provider-neutral bounded requests, responses, and error taxonomy."""
from dataclasses import dataclass
from model_registry import receipt_identity


class ProviderError(RuntimeError):
    def __init__(self, kind, message):
        self.kind = kind
        super().__init__(message)


@dataclass(frozen=True)
class ModelRequest:
    task_id: str
    model: str
    messages: list
    schema: dict
    max_tokens: int = 1200

    def __post_init__(self):
        if (type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 4000
                or not self.messages or len(self.messages) > 6):
            raise ValueError('Invalid bounded model request.')


@dataclass(frozen=True)
class ModelResponse:
    provider: str
    requested_model: str
    served_model: str
    completion_id: str
    usage: dict
    latency_ms: float
    candidate: dict
    reservation: dict

    def receipt(self):
        return {**receipt_identity(self.requested_model, self.served_model),
                'provider': self.provider, 'completion_id': self.completion_id,
                'tokens': self.usage, 'latency_ms': round(self.latency_ms, 2), 'budget': self.reservation}
