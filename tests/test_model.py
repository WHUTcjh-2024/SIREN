import torch

from models.siren import NeuralImplicitField


def test_first_backward_pass_reaches_early_layers():
    model = NeuralImplicitField(hidden_dim=16, num_layers=2)
    x = torch.linspace(-1, 1, 16).unsqueeze(1)
    loss = model(x).square().mean()
    loss.backward()
    gradient = model.layers[0].linear.weight.grad
    assert gradient is not None
    assert torch.count_nonzero(gradient).item() > 0
