# Medical Prior Authorization — OpenEnv Environment

A realistic OpenEnv environment simulating insurance prior authorization review for medical procedures. See [medical_pa_env/README.md](medical_pa_env/README.md) for full documentation.

## Quick Start

```bash
# Install
pip install -e medical_pa_env/

# Run server
uvicorn medical_pa_env.server.app:app --host 0.0.0.0 --port 8000

# Docker
docker build -t medical-pa-env .
docker run -p 8000:8000 medical-pa-env

# Inference
export HF_TOKEN=your_token
python inference.py
```
