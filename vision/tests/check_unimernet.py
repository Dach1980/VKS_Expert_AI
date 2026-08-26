import torch

from unimernet.models import load_model


print("Loading...")

model = load_model(
    "unimernet",
    "default"
)

model.eval()


p = next(model.parameters())


print("DEVICE:", p.device)
print("DTYPE:", p.dtype)
print("MEAN:", p.abs().mean())
