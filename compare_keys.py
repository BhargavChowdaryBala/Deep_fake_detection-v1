import torch
from torchvision.models import convnext_base

model = convnext_base(weights=None)
tv_keys = list(model.state_dict().keys())
print("TOP 20 TORCHVISION KEYS:")
for k in tv_keys[:20]:
    print(k)

print("\nUSER MODEL KEYS (from previous inspection):")
# I'll just write down what I saw
# backbone.stem.0.weight: torch.Size([128, 3, 4, 4])
# backbone.stem.1.weight: torch.Size([128])
# backbone.stages.0.blocks.0.gamma: torch.Size([128])
# backbone.stages.0.blocks.0.conv_dw.weight: torch.Size([128, 1, 7, 7])
