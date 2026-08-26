from unimernet.models import load_model


model = load_model(
    "unimernet",
    "default"
)


print("MODEL OK")


msg = model.load_checkpoint(
    r"D:\Projects\VKS_Expert_AI\models\unimernet\pytorch_model.pth"
)


print("MISSING:")
print(len(msg.missing_keys))

print(msg.missing_keys[:20])


print("UNEXPECTED:")
print(len(msg.unexpected_keys))

print(msg.unexpected_keys[:20])
