# GPU Models Reference

Supported NVIDIA GPU models on Akash Network.

## GPU Configuration

### Basic GPU Request

```yaml
profiles:
  compute:
    ml:
      resources:
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
```

### Specific Model Request

```yaml
profiles:
  compute:
    ml:
      resources:
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: a100
```

### With VRAM and Interface

```yaml
profiles:
  compute:
    ml:
      resources:
        gpu:
          units: 2
          attributes:
            vendor:
              nvidia:
                - model: a100
                  ram: 80Gi
                  interface: sxm
```

## Available GPU Models

### Data Center GPUs

| Model | VRAM | Architecture | Best For |
|-------|------|--------------|----------|
| `a100` | 40GB/80GB | Ampere | Large model training, HPC |
| `rtxa6000` | 48GB | Ampere | Professional visualization, training |
| `a40` | 48GB | Ampere | Professional visualization |
| `v100` | 16GB/32GB | Volta | Training, HPC |
| `t4` | 16GB | Turing | Inference, light training |
| `l4` | 24GB | Ada Lovelace | Video processing, inference |
| `l40` | 48GB | Ada Lovelace | Training, visualization |
| `l40s` | 48GB | Ada Lovelace | Training, inference |
| `h100` | 80GB | Hopper | Large model training |

### Consumer/Prosumer GPUs

| Model | VRAM | Architecture | Best For |
|-------|------|--------------|----------|
| `rtx3060` | 12GB | Ampere | Light ML, gaming |
| `rtx3070` | 8GB | Ampere | Light ML, gaming |
| `rtx3080` | 10GB/12GB | Ampere | ML inference, training |
| `rtx3080ti` | 12GB | Ampere | ML inference, training |
| `rtx3090` | 24GB | Ampere | Training, inference |
| `rtx3090ti` | 24GB | Ampere | Training, inference |
| `rtx4070` | 12GB | Ada Lovelace | ML inference |
| `rtx4080` | 16GB | Ada Lovelace | ML training, inference |
| `rtx4090` | 24GB | Ada Lovelace | Training, inference |

## GPU Specifications

### Model String Format

```yaml
# Model only
nvidia:
  - model: a100

# Model with VRAM
nvidia:
  - model: a100
    ram: 80Gi

# Model with interface
nvidia:
  - model: a100
    interface: sxm

# Full specification
nvidia:
  - model: a100
    ram: 80Gi
    interface: sxm
```

### VRAM Options

Specify GPU memory requirements:

```yaml
# 40GB A100
nvidia:
  - model: a100
    ram: 40Gi

# 80GB A100
nvidia:
  - model: a100
    ram: 80Gi
```

### Interface Options

| Interface | Description |
|-----------|-------------|
| `pcie` | PCIe connected (standard) |
| `sxm` | SXM socket (NVLink capable) |

```yaml
nvidia:
  - model: a100
    interface: sxm  # For NVLink connectivity
```

## Multi-GPU Configurations

### Multiple GPUs of Same Type

```yaml
profiles:
  compute:
    training:
      resources:
        gpu:
          units: 4
          attributes:
            vendor:
              nvidia:
                - model: a100
                  interface: sxm
```

### GPU Requirements

When requesting multiple GPUs:
- Ensure sufficient CPU and memory
- Consider NVLink for multi-GPU training
- Scale memory with GPU count

```yaml
profiles:
  compute:
    multi-gpu:
      resources:
        cpu:
          units: 32        # Scale CPU with GPUs
        memory:
          size: 128Gi      # ~32GB per GPU
        storage:
          size: 500Gi
        gpu:
          units: 4
          attributes:
            vendor:
              nvidia:
                - model: a100
```

## Use Case Recommendations

### LLM Inference (Small Models)

```yaml
# Llama 2 7B, Mistral 7B
gpu:
  units: 1
  attributes:
    vendor:
      nvidia:
        - model: t4
```

### LLM Inference (Large Models)

```yaml
# Llama 2 70B, large models
gpu:
  units: 2
  attributes:
    vendor:
      nvidia:
        - model: a100
          ram: 80Gi
```

### Stable Diffusion

```yaml
gpu:
  units: 1
  attributes:
    vendor:
      nvidia:
        - model: rtx3090
```

### Training (Medium)

```yaml
gpu:
  units: 1
  attributes:
    vendor:
      nvidia:
        - model: a100
          ram: 40Gi
```

### Training (Large Scale)

```yaml
gpu:
  units: 8
  attributes:
    vendor:
      nvidia:
        - model: a100
          ram: 80Gi
          interface: sxm
```

## Provider Availability

Not all providers have all GPU models. Check availability:

1. **Console**: Filter by GPU type in deployment wizard
2. **CLI**: Query provider attributes
3. **Market**: Higher-end GPUs may have limited availability

## Pricing Expectations

GPU pricing varies by model and market conditions:

| GPU Tier | Examples | uact/block Range |
|----------|----------|------------------|
| Entry | T4, RTX 3060 | 5,000 - 15,000 |
| Mid | RTX 3080/3090 | 15,000 - 30,000 |
| High | A100 40GB, rtxa6000 | 30,000 - 60,000 |
| Top | A100 80GB, H100 | 60,000 - 150,000+ |

## Validation Rules

### GPU with units > 0 Must Have Vendor

```yaml
# INVALID
gpu:
  units: 1
# Missing vendor attribute

# VALID
gpu:
  units: 1
  attributes:
    vendor:
      nvidia:
```

### GPU with units = 0 Cannot Have Attributes

```yaml
# INVALID
gpu:
  units: 0
  attributes:
    vendor:
      nvidia:

# VALID
gpu:
  units: 0
```

## Docker Images for GPU Workloads

Common base images:

```yaml
# NVIDIA CUDA base
image: nvidia/cuda:12.0-runtime-ubuntu22.04

# PyTorch
image: pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

# TensorFlow
image: tensorflow/tensorflow:2.13.0-gpu

# Hugging Face TGI
image: ghcr.io/huggingface/text-generation-inference:1.1.0

# Triton Inference Server
image: nvcr.io/nvidia/tritonserver:23.08-py3
```
