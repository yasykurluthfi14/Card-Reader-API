import os
from flask import Flask, request, jsonify
from PIL import Image
import pytesseract
from scipy.signal import convolve2d
from scipy.ndimage import gaussian_filter
import numpy as np
from skimage import exposure
from functools import wraps
import secrets
from datetime import datetime
import json
import random
import string
from datetime import datetime, timedelta
from werkzeug.datastructures import MultiDict

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.config['SECRET_KEY'] = 'amyl140200' 
authorization_codes = {}
# app.config['API_TOKEN'] = secrets.token_hex(16)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

tesseract_config = r'--oem 3 --psm 6'

def generate_authorization_code():
    authorization_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return authorization_code

def generate_authorization_data():
    authorization_code = generate_authorization_code()
    expiry_time = datetime.now() + timedelta(minutes=10)
    authorization_codes[authorization_code] = expiry_time
    return authorization_code, expiry_time

def is_valid_authorization(authorization_code, expiry_time):
    current_time = datetime.now()
    return authorization_code in authorization_codes and current_time < expiry_time

@app.route('/generate-authorization-code', methods=['POST'])
def generate_authorization():
    authorization_code, expiry_time = generate_authorization_data()

    form_data = MultiDict([('authorization_code', authorization_code), ('expiry_time', expiry_time.isoformat())])
    return jsonify(form_data)

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

def generate_unique_filename(original_filename):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_hex = secrets.token_hex(8)
    file_extension = original_filename.rsplit('.', 1)[1] if '.' in original_filename else 'jpg'
    return f"{timestamp}_{random_hex}.{file_extension}"

def categorize_text(ocr_text):
    categories = {
        "NIK": [],
        "Nama": [],
        "Tempat/Tgl Lahir": [],
        "Jenis Kelamin": [],
        "Alamat": [],
        "RT/RW": [],
        "Kel/Desa": [],
        "Kecamatan": [],
        "Agama": [],
        "Status Perkawinan": [],
        "Pekerjaan": [],
        "Kewarganegaraan": [],
        "Berlaku Hingga": []
    }
    
    for line in ocr_text.split('\n'):
        if "NIK" in line:
            categories["NIK"].append(line)
        elif "Nama" in line:
            categories["Nama"].append(line)
        elif "Tempat/Tgl Lahir" in line:
            categories['Tempat/Tgl Lahir'].append(line)
        elif "Jenis Kelamin" in line:
            categories['Jenis Kelamin'].append(line)
        elif "Alamat" in line:
            categories['Alamat'].append(line)
        elif "RT/RW" in line:
            categories["RT/RW"].append(line)
        elif "Kel/Desa" in line:
            categories["Kel/Desa"].append(line)
        elif "Kecamatan" in line:
            categories["Kecamatan"].append(line)
        elif "Agama" in line:
            categories["Agama"].append(line)
        elif "Status Perkawinan" in line:
            categories["Status Perkawinan"].append(line)
        elif "Pekerjaan" in line:
            categories["Pekerjaan"].append(line)
        elif "Kewarganegaraan" in line:
            categories["Kewarganegaraan"].append(line)
        elif "Berlaku Hingga" in line:
            categories["Berlaku Hingga"].append(line)
    
    return categories

@app.route('/api/process', methods=['POST'])
def api_process():

    authorization_code = request.form.get('authorization_code')

    if is_valid_authorization(authorization_code, authorization_codes.get(authorization_code)):

        if 'file' not in request.files:
            return jsonify({'message': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400
        
        if file:
            filename = generate_unique_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            psf_size = 15
            psf_sigma = 1.5
            brightness_factor = 1.2

            image = Image.open(file_path)

            restored_image = restore_image(np.array(image), psf_size, psf_sigma, brightness_factor)
            restored_image = Image.fromarray((restored_image * 255).astype(np.uint8))
        
            ocr_text = pytesseract.image_to_string(restored_image, lang='ind', config=tesseract_config)

            reference_text = "NIK Nama Tempat/Tgl Lahir Alamat RT/RW Kel/Desa Kecamatan Agama Status Perkawinan Pekerjaan Kewarganegaraan Berlaku Hingga"
            
            accuracy = evaluate_ocr_accuracy(ocr_text, reference_text)

            categorized_text = categorize_text(ocr_text) 

            ocr_result = {
                "Success" : "TRUE",
                "Text": categorized_text,
                "Accuracy": accuracy
            }

            result_filename = os.path.join(app.config['RESULT_FOLDER'], f'OCR_{filename}.json')
            
            with open(result_filename, 'w') as json_file:
                json.dump(ocr_result, json_file, ensure_ascii=False, indent=4)

            return jsonify(ocr_result)
    
    else:
        return jsonify({'message': 'Kode otorisasi tidak valid atau sudah kedaluwarsa'}), 401


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['RESULT_FOLDER']):
        os.makedirs(app.config['RESULT_FOLDER'])

    app.run(debug=True)
