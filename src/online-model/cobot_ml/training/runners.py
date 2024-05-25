import copy
import time
import typing

import numpy as np
import torch
import tqdm
from torch import nn
from torch.optim.optimizer import Optimizer
from torch.utils import data


def run_training_epoch(
        model: nn.Module,
        data_loader: data.DataLoader,
        optimizer: Optimizer,
        criterion: typing.Callable,
        device: torch.device,
):
    """
    Function performing one training epoch.
    Args:
        :param model: Network on which epoch is performed.
        :param data_loader: Loader providing data to train from.
        :param optimizer: Optimizer which performs optimization of the training loss.
        :param criterion: Function to calculate training loss.
        :param device: Device where the data will be send.
    """
    model.train(True)
    losses = []
    for input, target in data_loader:
        input = input.to(device)
        target = target.to(device)
        optimizer.zero_grad()
        output = model(input)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
    return np.mean(losses)


def run_validation_epoch(
        model: nn.Module,
        data_loader: data.DataLoader,
        criterion: typing.Callable,
        device: torch.device,
):
    """
    Function performing one validation epoch.
    Args:
        :param device: Device where the data will be send.
        :param model: Network on which epoch is performed.
        :param data_loader: Loader providing data on which model is validated.
        :param criterion: Function to calculate validation loss.
        :param device: Device where the data will be send.
    """
    model.train(False)
    losses = []
    with torch.no_grad():
        for input, target in data_loader:
            input = input.to(device)
            target = target.to(device)
            output = model(input)
            loss = criterion(output, target)
            losses.append(loss.item())
    return np.mean(losses)


def run_inference(
        model: nn.Module, data_loader: data.DataLoader, device: torch.device,
):
    """
    Function performing inference on data from data_loader.
    Args:
        :param model: Network on which epoch is performed.
        :param data_loader: Loader providing data on which model is validated.
        :param device: Device where the data will be send.
    """
    model.train(False)
    outputs = []
    with torch.no_grad():
        for input, _ in data_loader:
            input = input.to(device)
            output = model(input)
            outputs.append(output)
    return torch.cat(outputs)


def run_training(
        model: nn.Module,
        loss: typing.Callable,
        optimizer: Optimizer,
        train_loader: data.DataLoader,
        valid_loader: data.DataLoader,
        number_of_epochs: int,
        patience: int,
        scheduler=None,
        device: torch.device = torch.device("cpu"),
) -> typing.Tuple[typing.Dict, typing.Dict]:
    """
    Run training on provided dataset
    :param model: Model to train
    :param loss: Loss function
    :param optimizer: Optimizer which performs optimization of the training loss.
    :param train_loader: Data loader of the training dataset
    :param valid_loader: Data loader of the validation dataset
    :param number_of_epochs: Duration of the training
    :param patience: Number of epochs after which the training will be terminated
        if the loss on validation dataset does not improve.
    :param scheduler: Learning rate scheduler
    :param device: Device to execute on
    :return: Best model's state dict and dict with training logs
    """
    best_loss = np.inf
    best_model_state = copy.deepcopy(model.state_dict())
    epochs_without_improvement = 0
    train_logs = {"train_loss": [], "valid_loss": [], "epoch_times": [], "best_epoch": 0, "epoch_count": 0}
    for epoch in tqdm.tqdm(range(number_of_epochs), desc="Training", unit="epoch"):
        tick = time.time()
        train_loss = run_training_epoch(
            model, train_loader, optimizer, loss, device=device
        )
        valid_loss = run_validation_epoch(model, valid_loader, loss, device=device)
        if scheduler is not None:
            scheduler.step(valid_loss)

        tock = time.time()
        train_logs["train_loss"].append(train_loss)
        train_logs["valid_loss"].append(valid_loss)
        train_logs["epoch_times"].append(tock - tick)
        train_logs["epoch_count"] = epoch

        print(f"train_loss={train_loss}, valid_loss={valid_loss}")
        if valid_loss < best_loss:
            best_loss = valid_loss
            train_logs["best_epoch"] = epoch
            best_model_state = copy.deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"Early stopping activated after {epoch} epochs")
                break
    return best_model_state, train_logs


def run_prediction(
        model: torch.nn.Module, data_loader: data.DataLoader
) -> torch.Tensor:
    model.train(False)
    outputs = []
    with torch.no_grad():
        for input in data_loader:
            output = model(input)
            outputs.append(output)
    return torch.cat(outputs)
