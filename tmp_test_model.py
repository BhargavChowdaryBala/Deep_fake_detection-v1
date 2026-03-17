import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

# Re-implementing classes from app.py to test
class LayerNorm(nn.Module):
    def __init__(self, normalized_shape, eps=1e-6, data_format="channels_last"):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(normalized_shape))
        self.bias = nn.Parameter(torch.zeros(normalized_shape))
        self.eps = eps
        self.data_format = data_format
        if self.data_format not in ["channels_last", "channels_first"]:
            raise NotImplementedError 
        self.normalized_shape = (normalized_shape, )
    
    def forward(self, x):
        if self.data_format == "channels_last":
            return F.layer_norm(x, self.normalized_shape, self.weight, self.bias, self.eps)
        elif self.data_format == "channels_first":
            u = x.mean(1, keepdim=True)
            s = (x - u).pow(2).mean(1, keepdim=True)
            x = (x - u) / torch.sqrt(s + self.eps)
            x = self.weight[:, None, None] * x + self.bias[:, None, None]
            return x

class Block(nn.Module):
    def __init__(self, dim, drop_path=0., layer_scale_init_value=1e-6):
        super().__init__()
        self.conv_dw = nn.Conv2d(dim, dim, kernel_size=7, padding=3, groups=dim) # depthwise conv
        self.norm = LayerNorm(dim, eps=1e-6)
        self.mlp = nn.ModuleDict({
            "fc1": nn.Linear(dim, 4 * dim),
            "act": nn.GELU(),
            "fc2": nn.Linear(4 * dim, dim)
        })
        self.gamma = nn.Parameter(layer_scale_init_value * torch.ones((dim)), 
                                    requires_grad=True) if layer_scale_init_value > 0 else None
        self.drop_path = nn.Identity()

    def forward(self, x):
        input = x
        x = self.conv_dw(x)
        x = x.permute(0, 2, 3, 1) # (N, C, H, W) -> (N, H, W, C)
        x = self.norm(x)
        x = self.mlp.fc1(x)
        x = self.mlp.act(x)
        x = self.mlp.fc2(x)
        if self.gamma is not None:
            x = self.gamma * x
        x = x.permute(0, 3, 1, 2) # (N, H, W, C) -> (N, C, H, W)
        x = input + self.drop_path(x)
        return x

class ConvNeXt(nn.Module):
    def __init__(self, in_chans=3, num_classes=2, 
                 depths=[3, 3, 27, 3], dims=[128, 256, 512, 1024], 
                 drop_path_rate=0., layer_scale_init_value=1e-6):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_chans, dims[0], kernel_size=4, stride=4),
            LayerNorm(dims[0], eps=1e-6, data_format="channels_first")
        )
        self.stages = nn.ModuleList()
        dp_rates=[x.item() for x in torch.linspace(0, drop_path_rate, sum(depths))] 
        cur = 0
        for i in range(4):
            stage = nn.ModuleDict()
            if i > 0:
                stage['downsample'] = nn.Sequential(
                    LayerNorm(dims[i-1], eps=1e-6, data_format="channels_first"),
                    nn.Conv2d(dims[i-1], dims[i], kernel_size=2, stride=2),
                )
            
            stage['blocks'] = nn.Sequential(
                *[Block(dim=dims[i], drop_path=dp_rates[cur + j], 
                        layer_scale_init_value=layer_scale_init_value) for j in range(depths[i])]
            )
            self.stages.append(stage)
            cur += depths[i]

        self.head = nn.ModuleDict({
            "avgpool": nn.AdaptiveAvgPool2d((1, 1)),
            "norm": LayerNorm(dims[-1], eps=1e-6, data_format="channels_last")
        })

    def forward_features(self, x):
        x = self.stem(x)
        for i in range(4):
            if 'downsample' in self.stages[i]:
                x = self.stages[i]['downsample'](x)
            x = self.stages[i]['blocks'](x)
        # This is where the error likely occurs
        pooled = self.head['avgpool'](x)
        print(f"Shape after avgpool: {pooled.shape}")
        x = pooled.view(pooled.size(0), -1) # FIX APPLIED
        return self.head['norm'](x)

    def forward(self, x):
        x = self.forward_features(x)
        return x

class DeepfakeModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = ConvNeXt(depths=[3, 3, 27, 3], dims=[128, 256, 512, 1024])
        self.classifier = nn.Sequential(
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 2)
        )

    def forward(self, x):
        x = self.backbone(x)
        x = x.view(x.size(0), -1) # Flatten pooled features
        return self.classifier(x)

# Test the model
try:
    model = DeepfakeModel()
    input_tensor = torch.randn(1, 3, 224, 224)
    output = model(input_tensor)
    print(f"Output shape: {output.shape}")
except Exception as e:
    print(f"Error during forward pass: {e}")
