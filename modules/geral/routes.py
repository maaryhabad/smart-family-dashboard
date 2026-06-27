import os
from flask import Blueprint, render_template, jsonify

geral_bp = Blueprint('geral', __name__)

@geral_bp.route('/')
def index():
    return render_template('index.html')

@geral_bp.route('/api/nas-status')
def get_nas_status():
    try:
        drive_letter = os.path.splitdrive(os.path.abspath(__file__))[0] or "E:"
    except Exception:
        drive_letter = "E:"
        
    return jsonify({
        "status": "Online",
        "connection_type": "USB 3.0 (Adaptador NVMe)",
        "drive_letter": drive_letter,
        "disk_total_gb": 1024,
        "disk_used_gb": 184,
        "disk_free_gb": 840,
        "disk_percentage": 18.0,
        "temperature_c": 38,
        "device_model": "Crucial P3 Plus NVMe SSD"
    })
