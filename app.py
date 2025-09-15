from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Simple file-based storage
LICENSES_FILE = "server_licenses.json"

def load_licenses():
    if os.path.exists(LICENSES_FILE):
        with open(LICENSES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_licenses(licenses):
    with open(LICENSES_FILE, 'w') as f:
        json.dump(licenses, f, indent=2)

@app.route('/api/license/check', methods=['POST'])
def check_license():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    machine_id = data.get('machine_id')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'})
    
    licenses = load_licenses()
    
    # Find license by email
    license_data = None
    for license_key, license_info in licenses.items():
        if license_info.get('contact_email') == email and license_info.get('password') == password:
            license_data = license_info
            break
    
    if not license_data:
        return jsonify({'success': False, 'message': 'Invalid email or password'})
    
    if not license_data.get('active', False):
        return jsonify({'success': True, 'active': False, 'message': 'License is inactive'})
    
    # Check expiry
    expires_at = license_data.get('expires_at')
    if expires_at and datetime.now().date() > datetime.strptime(expires_at, '%Y-%m-%d').date():
        return jsonify({'success': True, 'active': False, 'message': 'License expired'})
    
    # Check machine limits
    machine_ids = license_data.get('machine_ids', '').split(',')
    if machine_id not in machine_ids and len(machine_ids) >= license_data.get('seats', 1):
        return jsonify({'success': True, 'active': False, 'message': 'Seat limit exceeded'})
    
    return jsonify({'success': True, 'active': True, 'message': 'License valid'})

@app.route('/api/license/update', methods=['POST'])
def update_license():
    data = request.json
    license_key = data.get('license_key')
    
    licenses = load_licenses()
    if license_key in licenses:
        licenses[license_key].update({
            'active': data.get('active', licenses[license_key].get('active')),
            'expires_at': data.get('expires_at', licenses[license_key].get('expires_at')),
            'seats': data.get('seats', licenses[license_key].get('seats'))
        })
        save_licenses(licenses)
        return jsonify({'success': True, 'message': 'License updated'})
    
    return jsonify({'success': False, 'message': 'License not found'})

@app.route('/api/license/create', methods=['POST'])
def create_license():
    data = request.json
    license_key = data.get('license_key')
    email = data.get('contact_email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'})
    
    licenses = load_licenses()
    if license_key in licenses:
        return jsonify({'success': False, 'message': 'License already exists'})
    
    licenses[license_key] = {
        'agency_name': data.get('agency_name', ''),
        'contact_email': email,
        'password': data.get('password', ''),
        'active': data.get('active', True),
        'expires_at': data.get('expires_at', ''),
        'seats': data.get('seats', 1),
        'machine_ids': data.get('machine_ids', ''),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    save_licenses(licenses)
    return jsonify({'success': True, 'message': 'License created'})

@app.route('/')
def home():
    return jsonify({'message': 'Unseen Elementz License Server v1.0', 'status': 'online'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
