"""
训练模块 (v10 - MSE + PINN物理约束)
PINN约束: 光滑性正则化 + 对称性约束
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR


class Trainer:
    def __init__(self, model, config: dict, device='cpu'):
        self.model = model
        self.config = config
        self.device = device
        self.model.to(device)

        lr = config.get('learning_rate', 1e-4)
        wd = config.get('weight_decay', 1e-6)
        self.optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)

        self.mse = nn.MSELoss()
        self.pinn_weight = config.get('pinn_weight', 0.01)
        self.symmetry_weight = config.get('symmetry_weight', 0.005)
        self.scheduler = None
        self.training_history = []

    def _pinn_smoothness_loss(self, y_coords):
        y_in = y_coords.clone().detach().requires_grad_(True)
        I = self.model(y_in)
        dI = torch.autograd.grad(I, y_in, grad_outputs=torch.ones_like(I),
                                  create_graph=True, retain_graph=True)[0]
        d2I = torch.autograd.grad(dI, y_in, grad_outputs=torch.ones_like(dI),
                                  create_graph=True, retain_graph=True)[0]
        return (d2I ** 2).mean()

    def _pinn_symmetry_loss(self, y_coords):
        y_in = y_coords.clone().detach().requires_grad_(True)
        I = self.model(y_in)
        y_neg = -y_in
        I_neg = self.model(y_neg)
        return self.mse(I, I_neg)

    def train_step(self, y_coords, observed):
        self.model.train()
        self.optimizer.zero_grad()

        predicted = self.model(y_coords)
        loss_mse = self.mse(predicted, observed)

        loss_pinn = self._pinn_smoothness_loss(y_coords)
        loss_sym = self._pinn_symmetry_loss(y_coords)

        total_loss = loss_mse + self.pinn_weight * loss_pinn + self.symmetry_weight * loss_sym

        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()

        return {
            'total_loss': total_loss.item(),
            'loss_mse': loss_mse.item(),
            'loss_pinn': loss_pinn.item(),
            'loss_sym': loss_sym.item()
        }

    def train(self, y_coords, observed, epochs=500, verbose=True, progress_callback=None):
        from tqdm import tqdm

        self.training_history = []

        if self.scheduler is None:
            self.scheduler = CosineAnnealingLR(self.optimizer, T_max=epochs)

        patience = self.config.get('early_stopping_patience', 80)
        min_delta = self.config.get('early_stopping_min_delta', 1e-6)
        best_loss = float('inf')
        patience_counter = 0

        pbar = tqdm(range(epochs), desc="Training") if verbose else range(epochs)

        for epoch in pbar:
            loss_dict = self.train_step(y_coords, observed)
            self.training_history.append(loss_dict)
            self.scheduler.step()

            current_loss = loss_dict['total_loss']

            if current_loss < best_loss - min_delta:
                best_loss = current_loss
                patience_counter = 0
            else:
                patience_counter += 1

            if verbose:
                pbar.set_postfix({
                    'loss': f'{current_loss:.6f}',
                    'mse': f'{loss_dict["loss_mse"]:.6f}',
                    'pinn': f'{loss_dict["loss_pinn"]:.6f}'
                })

            if progress_callback:
                progress_callback(epoch + 1, epochs, {
                    'total_loss': loss_dict['total_loss'],
                    'loss_mse': loss_dict['loss_mse'],
                    'best_loss': best_loss,
                })

            if patience_counter >= patience:
                if verbose:
                    print(f'Early stopping at epoch {epoch + 1}, best loss: {best_loss:.6f}')
                break

        return self.training_history
