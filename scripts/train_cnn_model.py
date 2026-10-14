"""Train Model A: CNN HAB Detector on Sentinel-3 CIcyano GeoTIFF images.

The script auto-labels images using the CIcyano band pixel statistics:
  - Images whose median CI-cyano pixel > CYANO_THRESHOLD are labeled HAB=1
  - Others are labeled HAB=0

A lightweight ResNet-18 transfer learning model is trained for binary
classification.  The trained model state dict is saved to:
  models/detection/model.pt

Usage:
    python scripts/train_cnn_model.py \
        --images data/images \
        --model  models/detection/model.pt
"""

import argparse
import json
import logging
from datetime import date
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Pixels above this percentile of the whole-dataset CIcyano distribution
# are considered indicative of a bloom
CYANO_THRESHOLD_PERCENTILE = 75


# ── Dataset ────────────────────────────────────────────────────────────────────

class TifImageDataset(Dataset):
    """Simple dataset of GeoTIFF patches with binary HAB labels."""

    def __init__(self, paths: list[Path], labels: list[int], transform=None):
        self.paths = paths
        self.labels = labels
        self.transform = transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx):
        img_path = self.paths[idx]
        # Open with PIL (converts to 3-channel RGB automatically)
        img = Image.open(img_path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        label = torch.tensor(self.labels[idx], dtype=torch.long)
        return img, label


# ── Auto-labeling from CIcyano band ────────────────────────────────────────────

def auto_label_images(image_dir: Path) -> tuple[list[Path], list[int]]:
    """
    Find all CIcyano .tif files, compute their median pixel values,
    and label the top percentile as HAB=1.
    """
    cyano_files = sorted(image_dir.glob("*CIcyano*.tif"))
    if not cyano_files:
        raise FileNotFoundError(f"No CIcyano .tif files found in {image_dir}")

    log.info("Found %d CIcyano images", len(cyano_files))

    medians = []
    for f in cyano_files:
        arr = np.array(Image.open(f).convert("L"), dtype=float)
        medians.append(float(np.median(arr)))

    threshold = np.percentile(medians, CYANO_THRESHOLD_PERCENTILE)
    log.info(
        "CIcyano median stats — min=%.1f, max=%.1f, p75=%.1f (threshold)",
        min(medians), max(medians), threshold,
    )

    labels = [1 if m >= threshold else 0 for m in medians]
    hab_count = sum(labels)
    log.info("Auto-labels: HAB=%d, No-HAB=%d", hab_count, len(labels) - hab_count)
    return cyano_files, labels


# ── Training ────────────────────────────────────────────────────────────────────

def build_model(num_classes: int = 2, freeze_backbone: bool = True) -> nn.Module:
    """ResNet-18 pretrained backbone with replaced classifier head."""
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False
    # Replace final fully-connected layer
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(in_features, num_classes),
    )
    return model


def train_epoch(model, loader, optimizer, criterion, device):
    model.train()
    running_loss = 0.0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * images.size(0)
    return running_loss / len(loader.dataset)


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    all_preds, all_probs, all_labels = [], [], []
    for images, labels in loader:
        images = images.to(device)
        outputs = model(images)
        probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()
        preds = outputs.argmax(dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_probs.extend(probs)
        all_labels.extend(labels.numpy())
    return np.array(all_labels), np.array(all_preds), np.array(all_probs)


def train_cnn(
    image_dir: Path,
    model_path: Path,
    metadata_path: Path,
    epochs: int = 20,
    batch_size: int = 8,
    lr: float = 1e-3,
) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Training on device: %s", device)

    paths, labels = auto_label_images(image_dir)

    if len(set(labels)) < 2:
        raise ValueError("Need images from both HAB and No-HAB classes. Try lowering CYANO_THRESHOLD_PERCENTILE.")
    if len(paths) < 4:
        raise ValueError("At least 4 images required for train/test split.")

    # Stratified train/test split
    train_paths, test_paths, train_labels, test_labels = train_test_split(
        paths, labels, test_size=0.2, random_state=42, stratify=labels
    )
    log.info("Train=%d, Test=%d", len(train_paths), len(test_paths))

    # Transforms
    train_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    train_ds = TifImageDataset(train_paths, train_labels, transform=train_tf)
    test_ds = TifImageDataset(test_paths, test_labels, transform=val_tf)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    model = build_model(num_classes=2, freeze_backbone=True).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.fc.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=8, gamma=0.5)

    best_f1, best_state = 0.0, None
    history = []

    for epoch in range(1, epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        y_true, y_pred, y_prob = evaluate(model, test_loader, device)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        history.append({"epoch": epoch, "train_loss": round(train_loss, 4), "val_f1": round(f1, 4)})
        log.info("Epoch %02d/%02d  loss=%.4f  val_f1=%.4f", epoch, epochs, train_loss, f1)
        if f1 >= best_f1:
            best_f1 = f1
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        scheduler.step()

    # Final evaluation with best weights
    model.load_state_dict(best_state)
    y_true, y_pred, y_prob = evaluate(model, test_loader, device)

    metrics = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(set(y_true)) > 1 else None,
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "test_images": len(y_true),
    }
    log.info("Final metrics: %s", {k: v for k, v in metrics.items() if k != "confusion_matrix"})

    # Save model
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, model_path)
    log.info("Model saved to %s", model_path)

    metadata = {
        "model_name": "ResNet-18 HAB Image Detector",
        "version": date.today().isoformat(),
        "architecture": "ResNet-18 (pretrained backbone, frozen) + Dropout + Linear(512→2)",
        "training_images": len(train_paths),
        "test_images": len(test_paths),
        "image_dir": str(image_dir),
        "label_method": f"CIcyano auto-labeling (p{CYANO_THRESHOLD_PERCENTILE} threshold)",
        "epochs": epochs,
        "metrics": metrics,
        "history": history,
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    log.info("Metadata saved to %s", metadata_path)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=Path("data/images"))
    parser.add_argument("--model", type=Path, default=Path("models/detection/model.pt"))
    parser.add_argument("--metadata", type=Path, default=Path("models/detection/model_metadata.json"))
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    result = train_cnn(
        args.images,
        args.model,
        args.metadata,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
