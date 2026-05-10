# LoRA adapters

Put trained LoRA adapter artifacts here when you want to version them in GitHub.

Recommended PEFT layout:

```text
ml_json_generator/lora_adapters/json_cad_qwen_lora/
  adapter_config.json
  adapter_model.safetensors
  README.md
```

Base models do not belong in this folder. Keep GGUF/full checkpoints out of Git and download them from Hugging Face or another model registry when needed.

This repository tracks adapter weight files in this folder with Git LFS.
