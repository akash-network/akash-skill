# Example: LLM Inference

Patterns for serving large language models on Akash. Covers the two dominant runtimes in practice (Ollama, vLLM), model persistence across restarts, OpenAI-compatible endpoints, and sizing by parameter count.

## Use Case

- Serving chat / completion / embedding APIs
- Drop-in OpenAI-compatible endpoints for agent frameworks
- Cost-efficient inference on entry-level GPUs
- Private / self-hosted inference

## Runtime Selection

| Runtime | Best for | Pros | Cons |
|---------|----------|------|------|
| **Ollama** | ≤14 B models, prototyping, small teams | Trivial setup, huge model library, OpenAI-compatible out of the box, CPU fallback | Lower throughput than vLLM at scale |
| **vLLM** | Production high-throughput serving, larger models | PagedAttention, continuous batching, very high tok/s | More config, image size, model-format constraints |
| **TGI** (Hugging Face) | Single-model HF-native serving | Official HF support | Less common in 2025+; most have moved to vLLM or Ollama |

## Ollama Pattern (recommended starting point)

Ollama exposes its native API on `11434` *and* an OpenAI-compatible surface at `/v1` (see Ollama docs). Point any OpenAI SDK at `http://<akash-uri>:11434/v1` — no code changes.

The pull-then-restart pattern ensures the model is fully cached in the blob store before the server starts serving requests:

```yaml
version: "2.0"

services:
  ollama:
    image: ollama/ollama:0.13.4
    expose:
      - port: 11434
        as: 11434
        to:
          - global: true
        http_options:
          read_timeout: 600000
          send_timeout: 600000
    env:
      - MODEL=gemma3:4b
    command:
      - /bin/sh
      - -c
      - |
        ollama serve &
        while ! ollama pull ${MODEL}; do
          echo "Waiting for ollama pull to succeed..."
          sleep 2.5
        done
        ollama list
        pkill ollama
        ollama serve

profiles:
  compute:
    ollama:
      resources:
        cpu:
          units: 4
        memory:
          size: 16Gi
        storage:
          size: 50Gi
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
  placement:
    dcloud:
      pricing:
        ollama:
          denom: uakt
          amount: 10000

deployment:
  ollama:
    dcloud:
      profile: ollama
      count: 1
```

Change `MODEL` to any tag from the [Ollama library](https://ollama.com/library) (`qwen2.5:7b`, `llama3.3:70b`, `gpt-oss:20b`, etc.). Scale RAM, storage, and GPU VRAM accordingly — see the sizing table below.

## vLLM Pattern (high-throughput production)

vLLM ships its own OpenAI-compatible server on port `8000`. Preferred for ≥7 B models in production where tok/s matters.

```yaml
version: "2.0"

services:
  vllm:
    image: vllm/vllm-openai:v0.6.3
    expose:
      - port: 8000
        as: 8000
        to:
          - global: true
        http_options:
          read_timeout: 600000
          send_timeout: 600000
    command:
      - sh
      - "-c"
      - vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000 --dtype bfloat16 --max-model-len 8192 --gpu-memory-utilization 0.92

profiles:
  compute:
    vllm:
      resources:
        cpu:
          units: 8
        memory:
          size: 32Gi
        storage:
          - name: default
            size: 20Gi
          - name: models
            size: 100Gi
            attributes:
              persistent: true
              class: beta2
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: a10
  placement:
    dcloud:
      pricing:
        vllm:
          denom: uakt
          amount: 25000

deployment:
  vllm:
    dcloud:
      profile: vllm
      count: 1
```

**Persistent model storage.** The `models` volume with `persistent: true` keeps downloaded weights across lease restarts. Without it, every restart re-downloads tens of GB from Hugging Face — slow and costly. Mount via vLLM's `--download-dir` flag or the `HF_HOME` env var if you want to target that volume explicitly.

## CPU-only Pattern (tiny models)

For models ≤3 B you can skip the GPU entirely. Throughput is modest (single-digit tok/s) but the deployment is a fraction of the price.

```yaml
version: "2.0"

services:
  ollama:
    image: ollama/ollama:0.13.4
    expose:
      - port: 11434
        as: 11434
        to:
          - global: true
    env:
      - MODEL=qwen2.5:1.5b
    command:
      - /bin/sh
      - -c
      - |
        ollama serve &
        while ! ollama pull ${MODEL}; do sleep 2.5; done
        pkill ollama
        ollama serve

profiles:
  compute:
    ollama:
      resources:
        cpu:
          units: 4
        memory:
          size: 8Gi
        storage:
          size: 20Gi
  placement:
    dcloud:
      pricing:
        ollama:
          denom: uakt
          amount: 2000

deployment:
  ollama:
    dcloud:
      profile: ollama
      count: 1
```

## Sizing Table

Rough guidelines for 4-bit-quantised models on single GPU:

| Model size | VRAM needed | RAM | Storage | Typical GPU | Runtime |
|-----------|-------------|-----|---------|-------------|---------|
| 1 – 3 B | ≤4 GB | 8 Gi | 20 Gi | T4, RTX 3060, or CPU | Ollama |
| 4 – 8 B | 6–8 GB | 16 Gi | 50 Gi | RTX 2070, 3060, A10 | Ollama |
| 13 – 14 B | 10–12 GB | 24 Gi | 80 Gi | RTX 3080, A10 | Ollama / vLLM |
| 30 – 34 B | 20–24 GB | 48 Gi | 150 Gi | RTX 3090, A10, A100-40 | vLLM |
| 70 B | 40–48 GB | 96 Gi | 300 Gi | A100-80, 2× A100-40 | vLLM |
| 120 B+ | 80+ GB | 160+ Gi | 500+ Gi | A100-80, H100, multi-GPU | vLLM |

Add ~20 % headroom on each row for KV cache and batching.

## Verifying the Deployment

Once the lease is active, Akash assigns a URI. Test the OpenAI-compatible endpoint:

```bash
# Ollama
curl http://<akash-uri>:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:4b",
    "messages": [{"role":"user","content":"Say hello in one word."}]
  }'

# vLLM
curl http://<akash-uri>:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role":"user","content":"Say hello in one word."}]
  }'
```

## Best Practices

1. **Always pin image tags.** `ollama/ollama:0.13.4`, `vllm/vllm-openai:v0.6.3` — never `:latest`. Model-format compatibility shifts between versions.
2. **Persist model weights** for any model ≥5 GB. A 70 GB re-download on every restart is wasted lease time.
3. **Set long HTTP timeouts** (`read_timeout`, `send_timeout` ≥ 600 000 ms). Cold starts and long completions routinely exceed the 30 s default.
4. **Right-size storage.** Weights + blob cache + scratch ≈ 2–3× model size. Under-provisioning causes the pull loop to hang.
5. **Prefer OpenAI-compatible runtimes.** Both Ollama and vLLM expose `/v1/chat/completions` — your clients become portable across any OpenAI-alike endpoint.
6. **Match GPU VRAM to quantised size**, not the full-precision parameter count. A 4-bit 7 B model fits in 6 GB VRAM; a bf16 7 B needs 14 GB+.
7. **For multi-model serving**, deploy a lightweight gateway (LiteLLM, Werner, custom proxy) in front of several single-model deployments rather than trying to swap models inside one lease.

## See Also

- `@sdl/examples/gpu-workload.md` — general GPU SDL patterns
- `@reference/gpu-models.md` — GPU attribute reference
- [awesome-akash](https://github.com/akash-network/awesome-akash) — production-ready LLM templates (search for Llama, Qwen, DeepSeek, Gemma)
- [Ollama docs](https://ollama.com/docs)
- [vLLM docs](https://docs.vllm.ai)
