
import os
import uuid
import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from google import genai
from google.genai import types

from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
from gfpgan import GFPGANer


# ==================================================
# APPLICATION CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
MODEL_FOLDER = BASE_DIR / "models"

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
MODEL_FOLDER.mkdir(exist_ok=True)

REAL_ESRGAN_PATH = MODEL_FOLDER / "RealESRGAN_x4plus.pth"
GFPGAN_PATH = MODEL_FOLDER / "GFPGANv1.4.pth"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp"
}

app = Flask(__name__)
CORS(app)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

upsampler = None
face_restorer = None


# ==================================================
# GEMINI CLIENT
# ==================================================

def get_gemini_client():

    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key is not configured.")

    return genai.Client(api_key=GEMINI_API_KEY)


def generate_gemini_with_retry(client, model, contents, config):

    max_attempts = 3

    for attempt in range(max_attempts):

        try:

            print(
                f"Gemini request attempt {attempt + 1}/{max_attempts}"
            )

            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )

        except Exception as error:

            message = str(error).upper()

            temporary_errors = [
                "503",
                "429",
                "500",
                "UNAVAILABLE",
                "RESOURCE_EXHAUSTED",
                "INTERNAL"
            ]

            is_temporary = any(
                code in message for code in temporary_errors
            )

            # Do not waste retries on exhausted daily quota.
            quota_exhausted = (
                "429" in message
                or "RESOURCE_EXHAUSTED" in message
            )

            if not is_temporary or quota_exhausted:
                raise

            if attempt == max_attempts - 1:
                raise

            wait_time = 2 ** (attempt + 1)

            print(f"Gemini busy. Retrying in {wait_time} seconds...")

            time.sleep(wait_time)


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def calculate_sharpness(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return round(
        float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        2
    )


def analyze_image_locally(image):

    """
    OpenCV-based fallback analysis.

    This measures visual image properties.
    It does not understand the semantic content of an image.
    """

    height, width = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 1. Sharpness
    sharpness = calculate_sharpness(image)

    if sharpness < 50:
        blur = "High blur detected. The image appears noticeably soft."
        sharpness_level = "Low"

    elif sharpness < 150:
        blur = "Moderate blur detected. Some image details may be unclear."
        sharpness_level = "Moderate"

    else:
        blur = "The image has relatively good sharpness."
        sharpness_level = "Good"

    # 2. Brightness
    brightness = float(np.mean(gray))

    if brightness < 70:
        brightness_description = "The image appears dark or underexposed."

    elif brightness > 190:
        brightness_description = "The image appears bright or potentially overexposed."

    else:
        brightness_description = "The image has a reasonably balanced brightness level."

    # 3. Contrast
    contrast = float(np.std(gray))

    if contrast < 35:
        contrast_description = "Low contrast detected."

    elif contrast > 80:
        contrast_description = "High contrast detected."

    else:
        contrast_description = "Moderate contrast detected."

    # 4. Noise estimate
    median = cv2.medianBlur(gray, 3)

    noise_map = cv2.absdiff(gray, median)

    noise_level = float(np.mean(noise_map))

    if noise_level < 5:
        noise_description = "Low visible noise estimate."

    elif noise_level < 12:
        noise_description = "Moderate noise estimate."

    else:
        noise_description = "High noise estimate. Image artifacts may be present."

    # 5. Dominant colours
    resized = cv2.resize(
        image,
        (100, 100),
        interpolation=cv2.INTER_AREA
    )

    pixels = resized.reshape(-1, 3).astype(np.float32)

    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        20,
        1.0
    )

    _, labels, centers = cv2.kmeans(
        pixels,
        3,
        None,
        criteria,
        3,
        cv2.KMEANS_PP_CENTERS
    )

    counts = np.bincount(labels.flatten())

    dominant_colors = []

    for index in np.argsort(counts)[::-1]:

        b, g, r = centers[index]

        dominant_colors.append(
            "#{:02X}{:02X}{:02X}".format(
                int(r), int(g), int(b)
            )
        )

    # 6. Overall condition
    if sharpness < 50 or noise_level > 12:
        condition = "Needs restoration"

    elif sharpness < 150 or contrast < 35:
        condition = "Moderate condition"

    else:
        condition = "Relatively good condition"

    return {

        "image_type": (
            "Image type cannot be identified by OpenCV alone. "
            "Manual content verification is recommended."
        ),

        "blur": blur,

        "noise": noise_description,

        "damage": (
            "Physical scratches, fading and discoloration "
            "cannot be reliably identified by these basic measurements."
        ),

        "text_readability": (
            "Text readability has not been semantically verified. "
            "Inspect small text manually."
        ),

        "logo_visibility": (
            "Logo visibility has not been semantically verified. "
            "Check original logos manually."
        ),

        "colors": (
            f"{brightness_description} {contrast_description} "
            f"Dominant colours: {', '.join(dominant_colors)}."
        ),

        "layout": (
            "Image dimensions and aspect ratio were measured. "
            "Semantic layout analysis requires a vision model."
        ),

        "faces_present": False,

        "restoration_recommendation": (
            "Consider Real-ESRGAN upscaling. "
            "Review text, logos, brand colours and layout manually "
            "after restoration."
        ),

        "overall_condition": condition,

        "technical_metrics": {

            "width": width,
            "height": height,
            "sharpness": sharpness,
            "sharpness_level": sharpness_level,
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "noise_estimate": round(noise_level, 2),
            "dominant_colors": dominant_colors

        }

    }


# ==================================================
# MODEL INITIALIZATION
# ==================================================

def load_models():

    global upsampler, face_restorer

    if upsampler is not None:
        return

    if not REAL_ESRGAN_PATH.exists():
        raise FileNotFoundError(
            f"Real-ESRGAN weights not found: {REAL_ESRGAN_PATH}"
        )

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
        model_path=str(REAL_ESRGAN_PATH),
        model=model,
        tile=256,
        tile_pad=10,
        pre_pad=0,
        half=(device.type == "cuda"),
        device=device
    )

    print("Real-ESRGAN loaded successfully.")

    if GFPGAN_PATH.exists():

        print("Loading GFPGAN model...")

        face_restorer = GFPGANer(
            model_path=str(GFPGAN_PATH),
            upscale=4,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=upsampler,
            device=device
        )

        print("GFPGAN loaded successfully.")

    else:

        print("GFPGAN weights not found.")


# ==================================================
# API: HOME
# ==================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "application": "BrandRestore AI",
        "status": "Backend running",
        "device": str(device)
    })


# ==================================================
# API: MODEL STATUS
# ==================================================

@app.route("/api/status", methods=["GET"])
def model_status():

    return jsonify({

        "backend": "running",

        "device": str(device),

        "cuda_available": torch.cuda.is_available(),

        "real_esrgan_weights": REAL_ESRGAN_PATH.exists(),

        "gfpgan_weights": GFPGAN_PATH.exists(),

        "real_esrgan_loaded": upsampler is not None,

        "gfpgan_loaded": face_restorer is not None,

        "gemini_configured": bool(GEMINI_API_KEY),

        "gemini_model": GEMINI_MODEL

    })


# ==================================================
# API: IMAGE ANALYSIS
# ==================================================

@app.route("/api/analyze", methods=["POST"])
def analyze_image_api():

    try:

        if "image" not in request.files:

            return jsonify({
                "success": False,
                "error": "No image uploaded."
            }), 400

        file = request.files["image"]

        if file.filename == "":

            return jsonify({
                "success": False,
                "error": "Please select an image."
            }), 400

        if not allowed_file(file.filename):

            return jsonify({
                "success": False,
                "error": "Unsupported image format."
            }), 400

        extension = file.filename.rsplit(".", 1)[1].lower()

        image_bytes = file.read()

        if not image_bytes:

            return jsonify({
                "success": False,
                "error": "Uploaded image is empty."
            }), 400

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if image is None:

            return jsonify({
                "success": False,
                "error": "Unable to read uploaded image."
            }), 400

        height, width = image.shape[:2]

        filename = secure_filename(file.filename)

        print("\nStarting image analysis...")
        print("Image:", filename)
        print("Dimensions:", width, "x", height)

        analysis = None
        analysis_source = None

        # Try Gemini when configured.
        if GEMINI_API_KEY:

            try:

                print("Trying Gemini image analysis...")

                client = get_gemini_client()

                prompt = """
You are an image quality analyst for BrandRestore AI.

Analyze this marketing or advertising creative.

Return valid JSON only, with these fields:

{
    "image_type": "Type of creative",
    "blur": "Description of blur and sharpness",
    "noise": "Description of noise and compression artifacts",
    "damage": "Scratches, fading or discoloration",
    "text_readability": "Condition of visible text",
    "logo_visibility": "Condition of visible logos",
    "colors": "Condition of colors",
    "layout": "Description of layout condition",
    "faces_present": true,
    "restoration_recommendation": "Recommended restoration approach",
    "overall_condition": "Overall image condition"
}

Use true or false for faces_present.

Do not invent details that are not visible.
Mention uncertainty when necessary.
Do not recommend changing original logos, text, brand colors or layout.
Do not claim that the image has already been restored.
Return JSON only.
"""

                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=MIME_TYPES[extension]
                )

                response = generate_gemini_with_retry(
                    client=client,
                    model=GEMINI_MODEL,
                    contents=[prompt, image_part],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )

                if not response.text:
                    raise RuntimeError("Gemini returned an empty response.")

                analysis = json.loads(response.text)

                analysis_source = "Gemini AI"

                print("Gemini analysis completed.")

            except Exception as gemini_error:

                print("Gemini unavailable:", str(gemini_error))
                print("Switching to OpenCV analysis...")

        else:

            print("Gemini API key not configured.")
            print("Using OpenCV fallback.")

        # OpenCV fallback
        if analysis is None:

            analysis = analyze_image_locally(image)

            analysis_source = "OpenCV Local Analysis"

            print("OpenCV analysis completed.")

        return jsonify({

            "success": True,

            "message": "Image analyzed successfully.",

            "filename": filename,

            "image_width": width,

            "image_height": height,

            "analysis": analysis,

            "model": analysis_source,

            "analysis_source": analysis_source

        })

    except Exception as error:

        print("IMAGE ANALYSIS ERROR:", str(error))

        return jsonify({

            "success": False,

            "error": str(error)

        }), 500


# ==================================================
# API: IMAGE RESTORATION
# ==================================================

@app.route("/api/restore", methods=["POST"])
def restore_image():

    try:

        if "image" not in request.files:

            return jsonify({
                "success": False,
                "error": "No image uploaded."
            }), 400

        file = request.files["image"]

        if file.filename == "":

            return jsonify({
                "success": False,
                "error": "Please select an image."
            }), 400

        if not allowed_file(file.filename):

            return jsonify({
                "success": False,
                "error": "Unsupported image format."
            }), 400

        try:

            scale = int(request.form.get("scale", 4))

        except (TypeError, ValueError):

            return jsonify({
                "success": False,
                "error": "Scale must be 2 or 4."
            }), 400

        if scale not in (2, 4):

            return jsonify({
                "success": False,
                "error": "Scale must be 2 or 4."
            }), 400

        face_enhance = (
            request.form.get("face_enhance", "false").lower()
            == "true"
        )

        load_models()

        unique_id = uuid.uuid4().hex[:10]

        original_name = secure_filename(file.filename)

        input_path = UPLOAD_FOLDER / f"{unique_id}_{original_name}"

        output_name = f"{unique_id}_restored.png"

        output_path = OUTPUT_FOLDER / output_name

        file.save(input_path)

        original = cv2.imread(
            str(input_path),
            cv2.IMREAD_COLOR
        )

        if original is None:

            return jsonify({
                "success": False,
                "error": "Unable to read uploaded image."
            }), 400

        original_height, original_width = original.shape[:2]

        original_sharpness = calculate_sharpness(original)

        print(
            f"Restoring {original_name} at {scale}x on {device}..."
        )

        if face_enhance:

            if face_restorer is None:

                return jsonify({
                    "success": False,
                    "error": "GFPGAN weights are not installed."
                }), 400

            _, _, restored = face_restorer.enhance(
                original,
                has_aligned=False,
                only_center_face=False,
                paste_back=True,
                weight=0.5
            )

        else:

            restored, _ = upsampler.enhance(
                original,
                outscale=scale
            )

        target_width = original_width * scale
        target_height = original_height * scale

        if (
            restored.shape[1] != target_width
            or restored.shape[0] != target_height
        ):

            restored = cv2.resize(
                restored,
                (target_width, target_height),
                interpolation=cv2.INTER_LANCZOS4
            )

        if not cv2.imwrite(str(output_path), restored):

            raise RuntimeError("Could not save restored image.")

        restored_sharpness = calculate_sharpness(restored)

        print("Restoration completed successfully.")

        return jsonify({

            "success": True,

            "message": "Image restored successfully.",

            "original_image": f"/api/uploads/{input_path.name}",

            "restored_image": f"/api/outputs/{output_name}",

            "original_width": original_width,

            "original_height": original_height,

            "restored_width": target_width,

            "restored_height": target_height,

            "scale": scale,

            "original_sharpness": original_sharpness,

            "restored_sharpness": restored_sharpness,

            "face_enhancement": face_enhance,

            "device": str(device)

        })

    except Exception as error:

        print("RESTORATION ERROR:", str(error))

        return jsonify({

            "success": False,

            "error": str(error)

        }), 500


# ==================================================
# API: SERVE IMAGES
# ==================================================

@app.route("/api/uploads/<filename>")
def get_uploaded_image(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


@app.route("/api/outputs/<filename>")
def get_restored_image(filename):

    return send_from_directory(
        OUTPUT_FOLDER,
        filename
    )


# ==================================================
# START SERVER
# ==================================================

if __name__ == "__main__":

    print("\n===================================")
    print("          BRANDRESTORE AI")
    print("===================================")

    print("Device:", device)
    print("CUDA available:", torch.cuda.is_available())
    print("Gemini configured:", bool(GEMINI_API_KEY))
    print("Gemini model:", GEMINI_MODEL)

    print("Starting backend server...")
    print("Address: http://127.0.0.1:5000")

    print("===================================\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
