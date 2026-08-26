from unimernet.models import load_model
import torch


print("Loading model...")

model = load_model(
    "unimernet",
    "default"
)

model.eval()


print("Model loaded")


weight = (
    model
    .model
    .model
    .encoder
    .embeddings
    .patch_embeddings
    .projection
    .conv1
    .weight
)


print("Shape:")
print(weight.shape)

print("Mean:")
print(weight.mean())

print("Std:")
print(weight.std())

print("First values:")
print(weight.flatten()[:10])
