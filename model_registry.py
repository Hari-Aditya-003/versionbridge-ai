"""Explicit model registry. Availability and evaluation are separate facts."""
import json
import os
import threading
import time
from urllib.request import Request, urlopen

MODELS = {
    'vultr': {
        'glm-5.3-flash': {'structured': True, 'evidence': 'V1 controlled fixtures 13/13'},
        'deepseek-v4.1-flash-1017': {'structured': True, 'evidence': 'V1 controlled fixtures 12/13'},
    },
    'ollama': {
        'qwen2.5-coder:1.5b-instruct-q4_K_M': {'structured': True, 'evidence': 'private Dell V1 baseline', 'max_context': 2048},
        'qwen2.5-coder:3b-instruct-q4_K_M': {'structured': True, 'evidence': 'unpromoted; explicit private evaluation only', 'max_context': 2048},
    },
}
_CACHE = None
_LOCK = threading.Lock()


def require_model(provider, model):
    if provider not in MODELS or model not in MODELS[provider]:
        raise ValueError('Unknown model ID. Register and validate it before use.')
    if provider == 'ollama' and ':3b-' in model and os.getenv('VERSIONBRIDGE_ALLOW_EXPERIMENTAL_LOCAL') != '1':
        raise ValueError('The 3B local profile requires an explicit evaluation opt-in.')
    return {'id': model, 'provider': provider, **MODELS[provider][model]}


def receipt_identity(requested, served):
    return {'requested_model': requested, 'served_model': served,
            'model_substitution': served != requested,
            'identity_verified': isinstance(served, str) and served == requested}


def catalog(*, refresh=False):
    """Worker-only fetch; never expose credentials, and never silently use stale data."""
    global _CACHE
    with _LOCK:
        if not refresh and _CACHE and time.time() - _CACHE['checked_at'] < 300:
            return _CACHE
        key = os.getenv('VULTR_API_KEY')
        if not key:
            raise RuntimeError('Vultr catalog validation requires worker credentials.')
        request = Request('https://api.vultrinference.com/v1/models', headers={'Authorization': 'Bearer '+key})
        try:
            with urlopen(request, timeout=10) as response:
                result = json.loads(response.read(2_000_000))
            items = result['data']
            if not isinstance(items, list) or len(items) > 10000:
                raise ValueError
            ids = [item['id'] for item in items if isinstance(item, dict) and isinstance(item.get('id'), str)]
            _CACHE = {'checked_at': time.time(), 'ids': ids, 'source': request.full_url}
            return _CACHE
        except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
            raise RuntimeError('Vultr model catalog unavailable; model availability is unverified.') from exc


def validate_available(provider, model):
    entry = require_model(provider, model)
    if provider == 'vultr' and model not in catalog()['ids']:
        raise RuntimeError('Configured model is absent from the current Vultr catalog.')
    return entry
