"""Compact CPU-only PyTorch MLP with validation-only early stopping."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import numpy as np
import torch
from torch import nn

from .base import ModelConfig


class _CompactMLP(nn.Module):
    def __init__(self, input_width: int, hidden_width: int) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_width, hidden_width),
            nn.ReLU(),
            nn.Linear(hidden_width, 1),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return cast(torch.Tensor, self.network(values).squeeze(1))


def fit_compact_mlp(
    features: np.ndarray,
    targets: np.ndarray,
    validation_features: np.ndarray,
    validation_targets: np.ndarray,
    config: ModelConfig,
    seed: int,
) -> Callable[[np.ndarray], np.ndarray]:
    """Fit a CPU MLP, selecting the epoch only by validation loss."""
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    model = _CompactMLP(
        input_width=features.shape[1],
        hidden_width=int(config.parameters.get("hidden_units", 24)),
    ).to("cpu")
    optimiser = torch.optim.Adam(
        model.parameters(), lr=float(config.parameters.get("learning_rate", 0.01))
    )
    loss_function = nn.BCEWithLogitsLoss()
    train_x = torch.as_tensor(np.array(features, dtype=np.float32, copy=True), device="cpu")
    train_y = torch.as_tensor(targets, dtype=torch.float32, device="cpu")
    validation_x = torch.as_tensor(
        np.array(validation_features, dtype=np.float32, copy=True), device="cpu"
    )
    validation_y = torch.as_tensor(validation_targets, dtype=torch.float32, device="cpu")
    max_epochs = int(config.parameters.get("max_epochs", 60))
    patience = int(config.parameters.get("patience", 8))
    best_loss = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    waiting_epochs = 0

    for _ in range(max_epochs):
        model.train()
        optimiser.zero_grad()
        loss_function(model(train_x), train_y).backward()
        optimiser.step()
        model.eval()
        with torch.no_grad():
            validation_loss = float(loss_function(model(validation_x), validation_y).item())
        if validation_loss < best_loss - 1e-10:
            best_loss = validation_loss
            best_state = {
                name: value.detach().clone() for name, value in model.state_dict().items()
            }
            waiting_epochs = 0
        else:
            waiting_epochs += 1
            if waiting_epochs >= patience:
                break

    if best_state is None:
        raise RuntimeError("MLP early stopping did not record a validation state")
    model.load_state_dict(best_state)
    model.eval()

    def predict(frame: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            logits = model(
                torch.as_tensor(np.array(frame, dtype=np.float32, copy=True), device="cpu")
            )
            attack_probability = torch.sigmoid(logits).cpu().numpy().astype(np.float64)
        return np.column_stack((1.0 - attack_probability, attack_probability))

    return predict
