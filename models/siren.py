"""
SIREN 神经隐式表示模块
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict


class SIRENLayer(nn.Module):
    def __init__(self, in_features: int, out_features: int,
                 freq_0: float = 30.0, is_first: bool = False):
        super().__init__()
        self.freq_0 = freq_0
        self.is_first = is_first
        self.linear = nn.Linear(in_features, out_features)
        if is_first:
            nn.init.uniform_(self.linear.weight, -1 / in_features, 1 / in_features)
        else:
            std = np.sqrt(6.0 / in_features) / freq_0
            nn.init.uniform_(self.linear.weight, -std, std)
        nn.init.zeros_(self.linear.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sin(self.freq_0 * self.linear(x))


class NeuralImplicitField(nn.Module):
    def __init__(self,
                 input_dim: int = 1,
                 hidden_dim: int = 256,
                 num_layers: int = 4,
                 freq_0: float = 30.0):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.freq_0 = freq_0

        self.layers = nn.ModuleList()
        self.layers.append(SIRENLayer(input_dim, hidden_dim, freq_0, is_first=True))
        for _ in range(num_layers - 1):
            self.layers.append(SIRENLayer(hidden_dim, hidden_dim, freq_0))

        self.head = nn.Linear(hidden_dim, 1)
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, y: torch.Tensor) -> torch.Tensor:
        if y.dim() == 1:
            y = y.unsqueeze(-1)
        x = y
        for layer in self.layers:
            x = layer(x)
        return self.head(x)

    @torch.enable_grad()
    def derivatives(self, y: torch.Tensor):
        if y.dim() == 1:
            y = y.unsqueeze(-1)
        y_in = y.clone().detach().requires_grad_(True)
        I = self.forward(y_in)
        dI = torch.autograd.grad(
            I, y_in, grad_outputs=torch.ones_like(I),
            create_graph=True, retain_graph=True
        )[0]
        d2I = torch.autograd.grad(
            dI, y_in, grad_outputs=torch.ones_like(dI),
            create_graph=True, retain_graph=True
        )[0]
        return I, dI, d2I


def create_siren_model(config: Dict) -> NeuralImplicitField:
    return NeuralImplicitField(
        input_dim=config.get('input_dim', 1),
        hidden_dim=config.get('hidden_dim', 256),
        num_layers=config.get('num_layers', 4),
        freq_0=config.get('freq_0', 30.0)
    )
