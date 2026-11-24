
/* ============================================
   BRANDRESTORE AI - FRONTEND JAVASCRIPT
   ============================================ */

const API_BASE = "http://127.0.0.1:5000";


// ============================================
// HTML ELEMENTS
// ============================================

const imageInput = document.getElementById("imageInput");
const dropZone = document.getElementById("dropZone");

const uploadedImage = document.getElementById("uploadedImage");
const imageName = document.getElementById("imageName");
const imageDetails = document.getElementById("imageDetails");

const imagePreview = document.getElementById("imagePreview");
const removeImage = document.getElementById("removeImage");

const analyzeButton = document.getElementById("analyzeButton");
const restoreButton = document.getElementById("restoreButton");

const analysisStatus = document.getElementById("analysisStatus");
const statusMessage = document.getElementById("statusMessage");

const analysisPanel = document.getElementById("analysisPanel");
const analysisContent = document.getElementById("analysisContent");
const analysisFilename = document.getElementById("analysisFilename");
const analysisRecommendation = document.getElementById("analysisRecommendation");
const analysisModel = document.getElementById("analysisModel");

const faceEnhance = document.getElementById("faceEnhance");

const originalResult = document.getElementById("originalResult");
const restoredResult = document.getElementById("restoredResult");

const comparisonContainer = document.getElementById("comparisonContainer");
const comparisonSlider = document.getElementById("comparisonSlider");
const comparisonDivider = document.getElementById("comparisonDivider");

const resultsPanel = document.getElementById("resultsPanel");


// ============================================
// VARIABLES
// ============================================

let selectedFile = null;
let previewURL = null;


// ============================================
// STATUS MESSAGES
// ============================================

function setStatus(message) {
    if (statusMessage) {
        statusMessage.textContent = message;
    }
}

function setAnalysisStatus(message) {
    if (analysisStatus) {
        analysisStatus.textContent = message;
    }
}


// ============================================
// SETTINGS
// ============================================

function getSelectedScale() {
    const selected = document.querySelector(
        'input[name="scale"]:checked'
    );

    return selected ? selected.value : "4";
}

function getFaceEnhancement() {
    return faceEnhance ? faceEnhance.checked : false;
}


// ============================================
// BEFORE AND AFTER COMPARISON SLIDER
// ============================================

function updateComparison() {

    if (
        !comparisonSlider ||
        !comparisonDivider ||
        !originalResult
    ) {
        return;
    }

    const value = Number(comparisonSlider.value);

    originalResult.style.clipPath =
        `inset(0 ${100 - value}% 0 0)`;

    comparisonDivider.style.left = value + "%";
}

if (comparisonSlider) {

    comparisonSlider.addEventListener(
        "input",
        updateComparison
    );

    updateComparison();

    console.log("Comparison slider initialized.");
}


// ============================================
// IMAGE VALIDATION AND PREVIEW
// ============================================

function displayImage(file) {

    if (!file) return;

    const allowedTypes = [
        "image/png",
        "image/jpeg",
        "image/webp"
    ];

    if (!allowedTypes.includes(file.type)) {
        alert("Please upload a PNG, JPG, JPEG or WEBP image.");
        return;
    }

    const maxSize = 10 * 1024 * 1024;

    if (file.size > maxSize) {
        alert("Image size must be less than 10 MB.");
        return;
    }

    if (previewURL) {
        URL.revokeObjectURL(previewURL);
    }

    selectedFile = file;
    previewURL = URL.createObjectURL(file);

    const image = new Image();

    image.onload = function () {

        if (uploadedImage) {
            uploadedImage.src = previewURL;
        }

        if (imageName) {
            imageName.textContent = file.name;
        }

        if (imageDetails) {
            imageDetails.textContent =
                image.width + " × " + image.height +
                " pixels · " +
                (file.size / 1024).toFixed(1) + " KB";
        }

        if (imagePreview) {
            imagePreview.classList.add("visible");
        }

        if (analyzeButton) {
            analyzeButton.disabled = false;
        }

        if (restoreButton) {
            restoreButton.disabled = false;
        }

        // Show original image in comparison
        if (originalResult) {
            originalResult.src = previewURL;
            originalResult.style.clipPath = "inset(0 50% 0 0)";
        }

        // Clear previous restoration
        if (restoredResult) {
            restoredResult.removeAttribute("src");
        }

        // Hide previous comparison
        if (comparisonContainer) {
            comparisonContainer.classList.remove("ready");
        }

        // Hide previous results
        if (resultsPanel) {
            resultsPanel.hidden = true;
        }

        if (comparisonSlider) {
            comparisonSlider.value = 50;
        }

        updateComparison();

        // Clear previous analysis
        if (analysisPanel) {
            analysisPanel.hidden = true;
        }

        if (analysisContent) {
            analysisContent.replaceChildren();
        }

        // Remove previous download link
        const oldDownload = document.getElementById(
            "restoredDownloadLink"
        );

        if (oldDownload) {
            oldDownload.remove();
        }

        setAnalysisStatus(
            "Image uploaded. Ready for image analysis."
        );

        setStatus("Image uploaded. Ready to restore.");

        console.log("Image selected:", file.name);
    };

    image.onerror = function () {

        alert("Unable to read this image.");

        selectedFile = null;

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
            previewURL = null;
        }

        if (analyzeButton) analyzeButton.disabled = true;
        if (restoreButton) restoreButton.disabled = true;
    };

    image.src = previewURL;
}


// ============================================
// FILE INPUT
// ============================================

if (imageInput) {

    imageInput.addEventListener("change", function () {

        const file = this.files[0];

        if (file) {
            displayImage(file);
        }

    });

}


// ============================================
// DRAG AND DROP
// ============================================

if (dropZone) {

    dropZone.addEventListener("dragover", function (event) {

        event.preventDefault();
        dropZone.classList.add("drag-over");

    });

    dropZone.addEventListener("dragleave", function () {

        dropZone.classList.remove("drag-over");

    });

    dropZone.addEventListener("drop", function (event) {

        event.preventDefault();

        dropZone.classList.remove("drag-over");

        const file = event.dataTransfer.files[0];

        if (file) {
            displayImage(file);
        }

    });

}


// ============================================
// REMOVE IMAGE
// ============================================

if (removeImage) {

    removeImage.addEventListener("click", function (event) {

        event.preventDefault();

        selectedFile = null;

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
            previewURL = null;
        }

        if (imageInput) {
            imageInput.value = "";
        }

        if (uploadedImage) {
            uploadedImage.removeAttribute("src");
        }

        if (imagePreview) {
            imagePreview.classList.remove("visible");
        }

        if (originalResult) {
            originalResult.removeAttribute("src");
        }

        if (restoredResult) {
            restoredResult.removeAttribute("src");
        }

        if (comparisonContainer) {
            comparisonContainer.classList.remove("ready");
        }

        if (comparisonSlider) {
            comparisonSlider.value = 50;
        }

        updateComparison();

        if (resultsPanel) {
            resultsPanel.hidden = true;
        }

        if (analysisPanel) {
            analysisPanel.hidden = true;
        }

        if (analysisContent) {
            analysisContent.replaceChildren();
        }

        const oldDownload = document.getElementById(
            "restoredDownloadLink"
        );

        if (oldDownload) {
            oldDownload.remove();
        }

        if (analyzeButton) {
            analyzeButton.disabled = true;
        }

        if (restoreButton) {
            restoreButton.disabled = true;
        }

        setAnalysisStatus("Upload an image to analyze its quality.");
        setStatus("Upload an image to continue.");

        console.log("Image removed.");

    });

}


// ============================================
// DISPLAY IMAGE ANALYSIS
// ============================================

function displayAnalysis(data) {

    const analysis = data.analysis;

    if (!analysis || typeof analysis !== "object") {
        throw new Error("Backend did not return a valid analysis report.");
    }

    if (!analysisContent) {
        throw new Error("Analysis content element was not found.");
    }

    analysisContent.replaceChildren();

    const fields = [
        ["Image type", "image_type"],
        ["Blur and sharpness", "blur"],
        ["Noise and artifacts", "noise"],
        ["Image damage", "damage"],
        ["Text readability", "text_readability"],
        ["Logo visibility", "logo_visibility"],
        ["Colour condition", "colors"],
        ["Layout condition", "layout"]
    ];

    fields.forEach(function ([label, key]) {

        const card = document.createElement("div");
        card.className = "analysis-card";

        const heading = document.createElement("h3");
        heading.textContent = label;

        const description = document.createElement("p");
        const value = analysis[key];

        description.textContent =
            value !== undefined && value !== null
                ? String(value)
                : "Not provided by the analysis.";

        card.appendChild(heading);
        card.appendChild(description);

        analysisContent.appendChild(card);

    });

    // Faces detected card
    const facesCard = document.createElement("div");
    facesCard.className = "analysis-card";

    const facesHeading = document.createElement("h3");
    facesHeading.textContent = "Faces detected";

    const facesDescription = document.createElement("p");

    if (typeof analysis.faces_present === "boolean") {

        facesDescription.textContent =
            analysis.faces_present
                ? "Faces are present."
                : "No faces detected.";

    } else {

        facesDescription.textContent =
            "Face information was not provided.";

    }

    facesCard.appendChild(facesHeading);
    facesCard.appendChild(facesDescription);

    analysisContent.appendChild(facesCard);

    if (analysisFilename) {

        analysisFilename.textContent =
            "File: " +
            (data.filename || selectedFile?.name || "Unknown") +
            " · " +
            data.image_width + " × " +
            data.image_height + " pixels";

    }

    if (analysisRecommendation) {

        analysisRecommendation.textContent =
            analysis.restoration_recommendation ||
            "No restoration recommendation was provided.";

    }

    if (analysisModel) {

        analysisModel.textContent =
            "Analysis powered by " +
            (data.model || "Image analysis");

    }

    if (analysisPanel) {

        analysisPanel.hidden = false;

        analysisPanel.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }

}


// ============================================
// ANALYZE IMAGE
// ============================================

if (analyzeButton) {

    analyzeButton.addEventListener("click", async function (event) {

        event.preventDefault();

        if (!selectedFile) {
            alert("Please upload an image first.");
            return;
        }

        const formData = new FormData();
        formData.append("image", selectedFile);

        analyzeButton.disabled = true;
        analyzeButton.textContent = "Analyzing Image...";

        setAnalysisStatus(
            "AI is examining your image. Please wait..."
        );

        console.log("IMAGE ANALYSIS STARTED");

        try {

            const response = await fetch(
                `${API_BASE}/api/analyze`,
                {
                    method: "POST",
                    body: formData
                }
            );

            const data = await response.json();

            console.log("Analysis backend response:", data);

            if (!response.ok || !data.success) {

                throw new Error(
                    data.error ||
                    data.details ||
                    "Image analysis failed."
                );

            }

            displayAnalysis(data);

            setAnalysisStatus(
                "Image analysis completed successfully!"
            );

            console.log("IMAGE ANALYSIS COMPLETED");

        } catch (error) {

            console.error("IMAGE ANALYSIS ERROR:", error);

            setAnalysisStatus(
                "Analysis failed: " + error.message
            );

            alert(
                "Image analysis failed.\n\n" +
                error.message +
                "\n\nCheck the Flask terminal for details."
            );

        } finally {

            analyzeButton.disabled = !selectedFile;

            analyzeButton.textContent =
                "Analyze Image with Gemini →";

        }

    });

}


// ============================================
// DISPLAY RESTORATION RESULTS
// ============================================

function displayRestoredImage(data) {

    console.log("Displaying restoration result:", data);

    if (!data.success) {
        throw new Error(data.error || "Image restoration failed.");
    }

    if (!data.original_image || !data.restored_image) {

        throw new Error(
            "Backend did not return the original and restored image paths."
        );

    }

    if (!originalResult || !restoredResult) {
        throw new Error("Comparison image elements were not found.");
    }

    const originalURL = new URL(
        data.original_image,
        API_BASE
    ).href;

    const restoredURL = new URL(
        data.restored_image,
        API_BASE
    ).href;

    // Image loading diagnostics
    originalResult.onload = function () {
        console.log("Original image loaded successfully.");
    };

    originalResult.onerror = function () {
        console.error("Failed to load original image:", originalURL);
        setStatus("Original image could not be displayed.");
    };

    restoredResult.onload = function () {
        console.log("Restored image loaded successfully.");
        setStatus("Image restored successfully using AI!");
    };

    restoredResult.onerror = function () {
        console.error("Failed to load restored image:", restoredURL);
        setStatus("Restoration completed, but the result image could not be displayed.");
    };

    // Set images
    originalResult.src = originalURL;
    restoredResult.src = restoredURL;

    // Show results section
    if (resultsPanel) {
        resultsPanel.hidden = false;
    }

    // Show comparison
    if (comparisonContainer) {
        comparisonContainer.classList.add("ready");
    }

    // Reset slider
    if (comparisonSlider) {
        comparisonSlider.value = 50;
    }

    updateComparison();

    // Remove previous download link
    const oldDownload = document.getElementById(
        "restoredDownloadLink"
    );

    if (oldDownload) {
        oldDownload.remove();
    }

    // Create download link
    const downloadLink = document.createElement("a");

    downloadLink.id = "restoredDownloadLink";
    downloadLink.href = restoredURL;
    downloadLink.download = "BrandRestoreAI_Restored.png";
    downloadLink.textContent = "Download Restored Image";

    downloadLink.style.display = "inline-block";
    downloadLink.style.marginTop = "15px";
    downloadLink.style.padding = "12px 20px";
    downloadLink.style.background = "#263b30";
    downloadLink.style.color = "#ffffff";
    downloadLink.style.textDecoration = "none";
    downloadLink.style.borderRadius = "6px";

    restoredResult.parentElement.appendChild(downloadLink);

    console.log("Original dimensions:",
        data.original_width, "x", data.original_height);

    console.log("Restored dimensions:",
        data.restored_width, "x", data.restored_height);

    console.log("Scale:", data.scale + "x");
    console.log("Device:", data.device);

    setStatus("Image restoration completed. Loading result...");

    // Scroll to results
    if (resultsPanel) {

        resultsPanel.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }

}


// ============================================
// RESTORE IMAGE WITH REAL-ESRGAN
// ============================================

if (restoreButton) {

    restoreButton.addEventListener("click", async function (event) {

        // Prevent accidental page refresh
        event.preventDefault();

        console.log("RESTORE BUTTON CLICKED");

        if (!selectedFile) {
            alert("Please upload an image first.");
            return;
        }

        const formData = new FormData();

        formData.append("image", selectedFile);
        formData.append("scale", getSelectedScale());

        formData.append(
            "face_enhance",
            String(getFaceEnhancement())
        );

        if (analyzeButton) {
            analyzeButton.disabled = true;
        }

        restoreButton.disabled = true;
        restoreButton.textContent = "Restoring Image...";

        setStatus("AI is restoring your image. Please wait...");

        console.log("RESTORATION STARTED");
        console.log("Selected scale:", getSelectedScale());
        console.log("Face enhancement:", getFaceEnhancement());

        try {

            const response = await fetch(
                `${API_BASE}/api/restore`,
                {
                    method: "POST",
                    body: formData
                }
            );

            console.log("Backend HTTP status:", response.status);

            const data = await response.json();

            console.log("Restoration backend response:", data);

            if (!response.ok || !data.success) {

                throw new Error(
                    data.error ||
                    data.details ||
                    "Image restoration failed."
                );

            }

            displayRestoredImage(data);

            console.log("RESTORATION COMPLETED");

        } catch (error) {

            console.error("RESTORATION ERROR:", error);

            setStatus(
                "Unable to restore image: " + error.message
            );

            alert(
                "Unable to restore image.\n\n" +
                error.message +
                "\n\nCheck the browser console and Flask terminal."
            );

        } finally {

            if (analyzeButton) {
                analyzeButton.disabled = !selectedFile;
            }

            restoreButton.disabled = !selectedFile;

            restoreButton.textContent = "Restore Image →";

        }

    });

}


// ============================================
// CHECK BACKEND STATUS
// ============================================

async function checkBackendStatus() {

    try {

        const response = await fetch(
            `${API_BASE}/api/status`
        );

        if (!response.ok) {
            throw new Error("Backend is not responding.");
        }

        const data = await response.json();

        console.log("Backend status:", data);

        if (data.backend === "running") {
            console.log("BrandRestore AI backend connected.");
        }

    } catch (error) {

        console.error("Backend connection error:", error);

        setStatus(
            "Backend is not connected. Start the Flask server."
        );

    }

}


// ============================================
// INITIALIZE APPLICATION
// ============================================

checkBackendStatus();

console.log(
    "BrandRestore AI JavaScript loaded successfully."
);
