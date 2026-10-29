"""pip install torch segmentation-models-pytorch
Fine-tune a U-Net on xBD. Dataset class is a TODO: yield (post_image, mask) with classes 0..3."""
import torch, segmentation_models_pytorch as smp
from torch.utils.data import DataLoader

model = smp.Unet("resnet34", encoder_weights="imagenet", in_channels=3, classes=4)
loss_fn = smp.losses.DiceLoss(mode="multiclass")
opt = torch.optim.Adam(model.parameters(), lr=1e-4)

def train(dataset, epochs=10):
    loader = DataLoader(dataset, batch_size=8, shuffle=True)
    for ep in range(epochs):
        for img, mask in loader:
            opt.zero_grad(); loss = loss_fn(model(img), mask); loss.backward(); opt.step()
        print(f"epoch {ep} loss {loss.item():.4f}")
    torch.save(model.state_dict(), "models/unet_xbd.pt")
