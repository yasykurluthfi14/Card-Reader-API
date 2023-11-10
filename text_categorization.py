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
