
import cv2
import torch
from pathlib import Path
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

BASE = Path(__file__).resolve().parent
MODEL = BASE / "models" / "RealESRGAN_x4plus.pth"
INPUT = BASE / "uploads" / "Dillon-Blur-02.webp"
OUTPUT = BASE / "outputs" / "Dillon-Restored-Test.png"

print("GPU:", torch.cuda.get_device_name(0))
print("Loading Real-ESRGAN model...")

model = RRDBNet(
    num_in_ch=3,
    num_out_ch=3,
    num_feat=64,
    num_block=23,
    num_grow_ch=32,
    scale=4
)

upsampler = RealESRGANer(
    scale=4,
    model_path=str(MODEL),
    model=model,
    tile=256,
    tile_pad=10,
    pre_pad=0,
    half=True,
    device=torch.device("cuda")
)

print("Loading input image...")
image = cv2.imread(str(INPUT), cv2.IMREAD_COLOR)

if image is None:
    raise FileNotFoundError(f"Image not found: {INPUT}")

print("Original dimensions:", image.shape[1], "x", image.shape[0])
print("Restoring image on GPU...")

restored, _ = upsampler.enhance(image, outscale=4)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(OUTPUT), restored)

print("Restoration successful!")
print("Output dimensions:", restored.shape[1], "x", restored.shape[0])
print("Saved to:", OUTPUT)
