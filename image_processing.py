from PIL import Image
from scipy.signal import convolve2d
from scipy.ndimage import gaussian_filter
import numpy as np
from skimage import exposure
import pytesseract

def restore_image(blurry_image, psf_size, psf_sigma, brightness_factor):
    psf = gaussian_filter(np.zeros((psf_size, psf_size)), sigma=psf_sigma)
    psf[psf_size // 2, psf_size // 2] = 1.0
    psf /= np.sum(psf)

    restored_image = np.empty_like(blurry_image)
    for i in range(3):
        restored_image[:, :, i] = convolve2d(blurry_image[:, :, i], psf, mode='same', boundary='wrap')

    brightened_image = np.clip(brightness_factor * restored_image, 0, 255).astype(np.uint8)

    enhanced_image = exposure.equalize_adapthist(brightened_image)

    return enhanced_image

def evaluate_ocr_accuracy(ocr_results, reference_data):
    if not isinstance(ocr_results, str) or not isinstance(reference_data, str):
        return {
            "Precision": 0,
            "Recall": 0,
            "F1-Score": 0,
            "Overall Accuracy": 0
        }

    ocr_words = ocr_results.split()
    reference_words = reference_data.split()

    correct_count = 0
    total_ocr_count = len(ocr_words)
    total_reference_count = len(reference_words)

    if total_reference_count == 0:
        return {
            "Precision": 0,
            "Recall": 0,
            "F1-Score": 0,
            "Overall Accuracy": 0
        }

    for ocr_word in ocr_words:
        if ocr_word in reference_words:
            correct_count += 1

    precision = correct_count / total_ocr_count if total_ocr_count != 0 else 0
    recall = correct_count / total_reference_count
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) != 0 else 0
    overall_accuracy = correct_count / total_reference_count * 100

    return {
        "Precision": precision,
        "Recall": recall,
        "F1-Score": f1_score,
        "Overall Accuracy": overall_accuracy
    }
