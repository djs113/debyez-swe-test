import requests

test_files = [
    'data/samples/billing_002.xml',
    'data/samples/patient_001.xml'
]

for xml_file in test_files:
    filename_part = xml_file.split('/')[-1]
    print(f'\n=== Testing {filename_part} ===')
    
    with open(xml_file, 'rb') as f:
        files = {'file': f}
        response = requests.post('http://127.0.0.1:8000/upload', files=files)
    
    if response.status_code == 200:
        result = response.json()
        filename = result['filename']
        schema = result['detected_schema']
        print(f'Uploaded: {filename}')
        print(f'Detected schema: {schema}')
        
        # Generate PDF
        data = {'filename': filename, 'schema': schema}
        response = requests.post('http://127.0.0.1:8000/generate', data=data)
        
        if response.status_code == 200:
            print(f'PDF generated successfully')
        else:
            print(f'Error generating PDF: {response.status_code}')
            print(f'Details: {response.text}')
    else:
        print(f'Error uploading: {response.status_code}')
