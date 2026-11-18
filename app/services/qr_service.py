import os
import uuid
import qrcode
from PIL import Image, ImageDraw, ImageFont
from config import Config
from app.models import get_db_connection

def generate_qr_for_item(user_id, item_name, category, description, recovery_instructions, base_url="http://localhost:5000"):
    qr_uuid = str(uuid.uuid4())
    scan_url = f"{base_url}/qr/scan/{qr_uuid}"
    
    # Generate QR Code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(scan_url)
    qr.make(fit=True)
    
    # Create colored QR image (Dark Slate / Deep Indigo tone for premium look)
    qr_img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF").convert('RGB')
    
    # Save the QR Code image
    qr_dir = os.path.join(Config.UPLOAD_FOLDER, 'qr_codes')
    os.makedirs(qr_dir, exist_ok=True)
    filename = f"qr_{qr_uuid[:8]}.png"
    filepath = os.path.join(qr_dir, filename)
    qr_img.save(filepath)
    
    # Save registration to database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO qr_registrations (user_id, item_name, category, description, qr_code_uuid, recovery_instructions, qr_image_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, item_name, category, description, qr_uuid, recovery_instructions, filename))
    qr_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return qr_id, qr_uuid, filename
