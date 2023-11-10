from concurrent.futures import thread
from flask import Flask, request, jsonify, abort
from werkzeug.datastructures import MultiDict
from datetime import datetime, timedelta
import os
import secrets
from PIL import Image
import pytesseract
import numpy as np
import json
from nanonets import NANONETSOCR
from waitress import serve
from configmodule import ProductionConfig

from authorization import generate_authorization_code, generate_authorization_data, is_valid_authorization, authorization_codes
from image_processing import restore_image, evaluate_ocr_accuracy
from file_handling import generate_unique_filename, save_result_to_file
from text_categorization import categorize_text
from config import app_config

app = Flask(__name__)
app.config.from_object(ProductionConfig)
app.config['UPLOAD_FOLDER'] = app_config['UPLOAD_FOLDER']
app.config['RESULT_FOLDER'] = app_config['RESULT_FOLDER']
app.config['RESTORED_FOLDER'] = 'restored'
app.config['AUTHORIZATION'] = app_config['AUTHORIZATION']

def check_api_key():
    if request.path == '/generate-authorization-code':
        if 'Authorization' not in request.headers or request.headers['Authorization'] != app.config['AUTHORIZATION']:
            abort(401)

@app.route('/generate-authorization-code', methods=['POST'])
def generate_authorization():
    check_api_key() 
    
    authorization_code, expiry_time = generate_authorization_data()

    form_data = MultiDict([('authorization_code', authorization_code), ('expiry_time', expiry_time.isoformat())])
    return jsonify(form_data)

@app.route('/api/process', methods=['POST'])
def api_process():

    authorization_code = request.form.get('authorization_code')

    if is_valid_authorization(authorization_code, authorization_codes.get(authorization_code)):

        if 'file' not in request.files:
            return jsonify({'message': 'No file part',
                            'status': 'False'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'message': 'No selected file',
                            'status': 'False'}), 400
            
        allowed_extensions = {'jpg', 'png', 'jpeg'}
        
        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
            filename = generate_unique_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            psf_size = 15
            psf_sigma = 1.5
            brightness_factor = 1.2

            image = Image.open(file_path)

            restored_image = restore_image(np.array(image), psf_size, psf_sigma, brightness_factor)
            restored_image = Image.fromarray((restored_image * 255).astype(np.uint8))

            restored_image_path = os.path.join(app.config['RESTORED_FOLDER'], filename)
            restored_rgb_image = restored_image.convert('RGB')

            # Save the restored image
            restored_rgb_image.save(restored_image_path)

            model = NANONETSOCR()

            model.set_token('dbcac07d-7864-11ee-916a-1666fbc0f94c')

            ocr_text = model.convert_to_string(file_path, formatting='lines')
        
            # ocr_text = pytesseract.image_to_string(restored_image, lang='ind', config=tesseract_config)

            reference_text = "NIK Nama Tempat/Tgl Lahir Alamat RT/RW Kel/Desa Kecamatan Agama Status Perkawinan Pekerjaan Kewarganegaraan Berlaku Hingga"
            
            accuracy = evaluate_ocr_accuracy(ocr_text, reference_text)

            categorized_text = categorize_text(ocr_text) 

            if not categorized_text:
                ocr_result = {
                    "Status": "FALSE",
                    "Text": categorized_text,
                    "Accuracy": accuracy
                }           
            else:
                ocr_result = {
                    "Status": "TRUE",
                    "Text": categorized_text,
                    "Accuracy": accuracy
                }
                
            result_filename = os.path.join(app.config['RESULT_FOLDER'], f'OCR_{filename}.json')
            
            with open(result_filename, 'w') as json_file:
                json.dump(ocr_result, json_file, ensure_ascii=False, indent=4)

            return jsonify(ocr_result)
        else:
            return jsonify({'message': 'Invalid file extension. Allowed extensions are jpg, png, and jpeg.',
                            'status': 'False'}), 400
    
    else:
        return jsonify({'message': 'Kode otorisasi tidak valid atau sudah kedaluwarsa',
                        'status': 'False'}), 401

mode = 'dev'

if __name__ == '__main__':
    if mode == 'dev':
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        if not os.path.exists(app.config['RESULT_FOLDER']):
            os.makedirs(app.config['RESULT_FOLDER'])
        
        app.run(host='0.0.0.0', port=50100, debug=True)
    else:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        if not os.path.exists(app.config['RESULT_FOLDER']):
            os.makedirs(app.config['RESULT_FOLDER'])
        
        serve(app, host='0.0.0.0', port=50100, threads=2, url_prefix="/my-app")
        
        
    