"""Private loopback-only Ollama adapter with bounded tuning and unload-on-response."""
import http.client
import json
import os
import time
import gpu_guard
from providers.base import ModelResponse, ProviderError


def complete(request):
    gpu_guard.check()
    try:
        context = int(os.getenv('VERSIONBRIDGE_LOCAL_CONTEXT', '2048'))
        output = min(request.max_tokens, int(os.getenv('VERSIONBRIDGE_LOCAL_OUTPUT', '320')))
        if not 512 <= context <= 2048 or not 64 <= output <= 1200:
            raise ValueError('Local tuning exceeds the measured baseline bounds.')
        port = int(os.getenv('VERSIONBRIDGE_OLLAMA_PORT', '11434'))
        if not 1 <= port <= 65535:
            raise ValueError('Invalid loopback port.')
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=70)
        started = time.monotonic()
        try:
            body = json.dumps({'model': request.model, 'messages': request.messages, 'stream': False,
                               'format': request.schema, 'keep_alive': 0,
                               'options': {'num_ctx': context, 'num_predict': output, 'num_thread': 2, 'temperature': 0}})
            connection.request('POST', '/api/chat', body, {'Content-Type': 'application/json'})
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError('Ollama rejected the request.')
            result = json.loads(response.read(131072))
        finally:
            connection.close()
        if result.get('done') is not True:
            raise ValueError('Incomplete Ollama response.')
        answer = result['message']['content']
        candidate = json.loads(answer.strip().removeprefix('```json').removesuffix('```').strip())
        if not isinstance(candidate, dict):
            raise ValueError('Expected JSON object.')
        usage = {name: result[field] for name, field in [('prompt_tokens','prompt_eval_count'),('completion_tokens','eval_count')]
                 if type(result.get(field)) is int and result[field] >= 0}
        return ModelResponse('Ollama', request.model, result.get('model'), None, usage,
                             (time.monotonic()-started)*1000, candidate, {})
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError, http.client.HTTPException) as exc:
        raise ProviderError('transport_or_schema', 'Local inference failed. Check the model, tuning and SSH tunnel.') from exc
