# Example: GPU Workload

SDL configurations for GPU-accelerated workloads including machine learning, AI inference, and rendering.

## Use Case

- Machine learning training
- AI inference
- Video encoding/transcoding
- 3D rendering
- Scientific computing

## Basic GPU SDL

```yaml
version: "2.0"

services:
  ml:
    image: nvidia/cuda:12.0-runtime-ubuntu22.04
    command:
      - "nvidia-smi"
      - "-l"
      - "60"
    expose:
      - port: 8080
        as: 80
        to:
          - global: true

profiles:
  compute:
    ml:
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
        ml:
          denom: uakt
          amount: 10000

deployment:
  ml:
    dcloud:
      profile: ml
      count: 1
```

## GPU Model Selection

### NVIDIA A100 (High-end Training)

```yaml
version: "2.0"

services:
  training:
    image: pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime
    command:
      - "python"
      - "train.py"
    env:
      - "CUDA_VISIBLE_DEVICES=0"
    expose:
      - port: 6006
        as: 6006
        to:
          - global: true

profiles:
  compute:
    training:
      resources:
        cpu:
          units: 8
        memory:
          size: 64Gi
        storage:
          - name: default
            size: 10Gi
          - name: models
            size: 200Gi
            attributes:
              persistent: true
              class: beta2
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: a100
                  ram: 80Gi

  placement:
    dcloud:
      pricing:
        training:
          denom: uakt
          amount: 50000

deployment:
  training:
    dcloud:
      profile: training
      count: 1
```

### NVIDIA RTX 3090 (Cost-effective Training)

```yaml
version: "2.0"

services:
  training:
    image: tensorflow/tensorflow:2.13.0-gpu
    expose:
      - port: 8888
        as: 8888
        to:
          - global: true

profiles:
  compute:
    training:
      resources:
        cpu:
          units: 8
        memory:
          size: 32Gi
        storage:
          size: 100Gi
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: rtx3090

  placement:
    dcloud:
      pricing:
        training:
          denom: uakt
          amount: 20000

deployment:
  training:
    dcloud:
      profile: training
      count: 1
```

### NVIDIA T4 (Inference)

```yaml
version: "2.0"

services:
  inference:
    image: nvcr.io/nvidia/tritonserver:23.08-py3
    command:
      - "tritonserver"
      - "--model-repository=/models"
    expose:
      - port: 8000
        as: 8000
        to:
          - global: true
      - port: 8001
        as: 8001
        to:
          - global: true

profiles:
  compute:
    inference:
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
                - model: t4

  placement:
    dcloud:
      pricing:
        inference:
          denom: uakt
          amount: 15000

deployment:
  inference:
    dcloud:
      profile: inference
      count: 1
```

## Multi-GPU Configuration

```yaml
version: "2.0"

services:
  distributed-training:
    image: pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime
    env:
      - "WORLD_SIZE=4"
      - "MASTER_ADDR=localhost"
      - "MASTER_PORT=29500"
    expose:
      - port: 29500
        to:
          - global: true

profiles:
  compute:
    distributed-training:
      resources:
        cpu:
          units: 32
        memory:
          size: 128Gi
        storage:
          size: 500Gi
        gpu:
          units: 4
          attributes:
            vendor:
              nvidia:
                - model: a100
                  interface: sxm

  placement:
    dcloud:
      pricing:
        distributed-training:
          denom: uakt
          amount: 200000

deployment:
  distributed-training:
    dcloud:
      profile: distributed-training
      count: 1
```

## LLM Inference Example

```yaml
version: "2.0"

services:
  llm:
    image: ghcr.io/huggingface/text-generation-inference:1.1.0
    command:
      - "--model-id"
      - "meta-llama/Llama-2-7b-chat-hf"
      - "--port"
      - "8080"
    env:
      - "HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}"
    expose:
      - port: 8080
        as: 80
        to:
          - global: true
        http_options:
          read_timeout: 60000
          send_timeout: 60000

profiles:
  compute:
    llm:
      resources:
        cpu:
          units: 8
        memory:
          size: 32Gi
        storage:
          size: 100Gi
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: a100
                  ram: 40Gi

  placement:
    dcloud:
      pricing:
        llm:
          denom: uakt
          amount: 40000

deployment:
  llm:
    dcloud:
      profile: llm
      count: 1
```

## Stable Diffusion Example

```yaml
version: "2.0"

services:
  sd:
    image: stability-ai/stablediffusion:latest
    expose:
      - port: 7860
        as: 7860
        to:
          - global: true

profiles:
  compute:
    sd:
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
                - model: rtx3090

  placement:
    dcloud:
      pricing:
        sd:
          denom: uakt
          amount: 20000

deployment:
  sd:
    dcloud:
      profile: sd
      count: 1
```

## GPU Resource Guidelines

| GPU Model | VRAM | Typical Use Case | Price Range (uakt) |
|-----------|------|------------------|-------------------|
| T4 | 16GB | Inference | 10000-20000 |
| RTX 3080 | 10GB | Light training, inference | 15000-25000 |
| RTX 3090 | 24GB | Training, inference | 18000-30000 |
| A10 | 24GB | Training, inference | 25000-40000 |
| RTX A6000 | 48GB | Heavy training | 35000-50000 |
| A100 40GB | 40GB | Large models | 40000-60000 |
| A100 80GB | 80GB | Very large models | 60000-100000 |

## Best Practices

1. **Match GPU to workload**: Use T4 for inference, A100 for training
2. **Consider VRAM**: Large models need GPUs with sufficient memory
3. **Use persistent storage**: Store models and checkpoints persistently
4. **Set appropriate timeouts**: ML inference can be slow; increase HTTP timeouts
5. **Environment variables**: Pass model configs and tokens via env vars
