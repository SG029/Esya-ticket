from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import qrcode
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import uuid
import os
import io
import base64
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Firebase
try:
    # Initialize Firebase with service account key
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.getenv('FIREBASE_PROJECT_ID'),
        "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
        "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
        "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
        "client_id": os.getenv('FIREBASE_CLIENT_ID'),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL')
    })
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    db = None

def generate_qr_code(ticket_id):
    """Generate QR code for ticket validation"""
    validation_url = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/validate/{ticket_id}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(validation_url)
    qr.make(fit=True)
    
    # Create QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer.getvalue()

def send_email_with_qr(name, email, ticket_id, qr_code_data):
    """Send email with QR code ticket"""
    try:
        # Email configuration
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')
        
        if not all([sender_email, sender_password]):
            raise ValueError("Email credentials not configured")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"ESYA Fest <{sender_email}>"
        msg['To'] = email
        msg['Subject'] = f"🎉 Your ESYA Fest Ticket - {ticket_id[:8]}"
        
        # Email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">🎊 ESYA FEST 2025 🎊</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px;">Your Digital Ticket</p>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa;">
                <h2 style="color: #333; margin-bottom: 20px;">Hello {name}! 👋</h2>
                
                <p style="color: #555; font-size: 16px; line-height: 1.6;">
                    Congratulations! Your registration for ESYA Fest has been confirmed. 
                    Your unique ticket is attached as a QR code.
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #667eea;">
                    <h3 style="color: #333; margin-top: 0;">📋 Ticket Details</h3>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Ticket ID:</strong> {ticket_id}</p>
                    <p><strong>Status:</strong> ✅ Active</p>
                </div>
                
                <div style="background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #1976d2; margin-top: 0;">📱 How to Use Your Ticket</h3>
                    <ol style="color: #555; line-height: 1.8;">
                        <li>Save the QR code image to your phone</li>
                        <li>Present the QR code at the fest entrance</li>
                        <li>Our scanner will validate your entry</li>
                        <li>Enjoy the fest! 🎉</li>
                    </ol>
                </div>
                
                <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="color: #f57c00; margin: 0; font-weight: bold;">
                        ⚠️ Important: This ticket can only be used once. Keep it safe!
                    </p>
                </div>
                
                <p style="color: #555; font-size: 14px; margin-top: 30px;">
                    See you at ESYA Fest! 🚀<br>
                    - The ESYA Team
                </p>
            </div>
            
            <div style="background: #333; color: white; padding: 20px; text-align: center; font-size: 12px;">
                <p>ESYA Fest 2025 | Powered by QR Ticketing System</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach QR code
        qr_attachment = MIMEBase('application', 'octet-stream')
        qr_attachment.set_payload(qr_code_data)
        encoders.encode_base64(qr_attachment)
        qr_attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="ESYA_Ticket_{ticket_id[:8]}.png"'
        )
        msg.attach(qr_attachment)
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

@app.route('/')
def index():
    """Serve the frontend"""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ESYA Fest 2025 - Registration</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                max-width: 500px;
                width: 100%;
                text-align: center;
            }
            
            .logo {
                font-size: 48px;
                font-weight: bold;
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px;
            }
            
            .subtitle {
                color: #666;
                font-size: 18px;
                margin-bottom: 30px;
            }
            
            .form-group {
                margin-bottom: 25px;
                text-align: left;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 500;
            }
            
            input {
                width: 100%;
                padding: 15px;
                border: 2px solid #e1e5e9;
                border-radius: 10px;
                font-size: 16px;
                transition: all 0.3s ease;
                background: #f8f9fa;
            }
            
            input:focus {
                outline: none;
                border-color: #667eea;
                background: white;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .btn {
                width: 100%;
                padding: 18px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
            }
            
            .btn:disabled {
                opacity: 0.7;
                cursor: not-allowed;
                transform: none;
            }
            
            .loading {
                display: none;
                align-items: center;
                justify-content: center;
                gap: 10px;
                margin-top: 20px;
            }
            
            .spinner {
                width: 20px;
                height: 20px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .message {
                margin-top: 20px;
                padding: 15px;
                border-radius: 10px;
                display: none;
            }
            
            .success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 15px;
                margin-top: 30px;
                padding-top: 30px;
                border-top: 1px solid #e1e5e9;
            }
            
            .feature {
                text-align: center;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
            }
            
            .feature-icon {
                font-size: 24px;
                margin-bottom: 8px;
            }
            
            .feature-text {
                font-size: 12px;
                color: #666;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">ESYA</div>
            <div class="subtitle">College Fest 2025 🎉</div>
            
            <form id="registrationForm">
                <div class="form-group">
                    <label for="name">Full Name</label>
                    <input type="text" id="name" name="name" required placeholder="Enter your full name">
                </div>
                
                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" name="email" required placeholder="Enter your email">
                </div>
                
                <button type="submit" class="btn" id="submitBtn">
                    Register for ESYA Fest
                </button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <span>Generating your ticket...</span>
            </div>
            
            <div class="message" id="message"></div>
            
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">📱</div>
                    <div class="feature-text">QR Code Ticket</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">📧</div>
                    <div class="feature-text">Email Delivery</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🔒</div>
                    <div class="feature-text">Secure Entry</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">⚡</div>
                    <div class="feature-text">Instant Access</div>
                </div>
            </div>
        </div>
        
        <script>
            document.getElementById('registrationForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const name = document.getElementById('name').value.trim();
                const email = document.getElementById('email').value.trim();
                const submitBtn = document.getElementById('submitBtn');
                const loading = document.getElementById('loading');
                const message = document.getElementById('message');
                
                if (!name || !email) {
                    showMessage('Please fill in all fields', 'error');
                    return;
                }
                
                // Show loading
                submitBtn.disabled = true;
                loading.style.display = 'flex';
                message.style.display = 'none';
                
                try {
                    const response = await fetch('/register', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ name, email })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showMessage(
                            `🎉 Registration successful! Your ticket has been sent to ${email}. 
                            Check your inbox for the QR code. Ticket ID: ${data.ticket_id.substring(0, 8)}...`, 
                            'success'
                        );
                        document.getElementById('registrationForm').reset();
                    } else {
                        showMessage(data.error || 'Registration failed', 'error');
                    }
                } catch (error) {
                    showMessage('Network error. Please try again.', 'error');
                } finally {
                    submitBtn.disabled = false;
                    loading.style.display = 'none';
                }
            });
            
            function showMessage(text, type) {
                const message = document.getElementById('message');
                message.textContent = text;
                message.className = `message ${type}`;
                message.style.display = 'block';
                
                if (type === 'success') {
                    setTimeout(() => {
                        message.style.display = 'none';
                    }, 10000);
                }
            }
        </script>
    </body>
    </html>
    """)

@app.route('/register', methods=['POST'])
def register():
    """Register a new user and send QR code ticket"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        
        if not name or not email:
            return jsonify({'error': 'Name and email are required'}), 400
        
        # Generate unique ticket ID
        ticket_id = str(uuid.uuid4())
        
        # Generate QR code
        qr_code_data = generate_qr_code(ticket_id)
        
        # Store ticket in Firebase
        if db:
            ticket_data = {
                'ticket_id': ticket_id,
                'name': name,
                'email': email,
                'scanned': False,
                'created_at': datetime.now(),
                'scanned_at': None
            }
            
            db.collection('tickets').document(ticket_id).set(ticket_data)
        
        # Send email with QR code
        email_sent = send_email_with_qr(name, email, ticket_id, qr_code_data)
        
        if not email_sent:
            return jsonify({'error': 'Failed to send email. Please try again.'}), 500
        
        return jsonify({
            'message': 'Registration successful! Check your email for the QR code.',
            'ticket_id': ticket_id
        }), 201
        
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/validate/<ticket_id>')
def validate_ticket(ticket_id):
    """Validate and mark ticket as scanned"""
    try:
        if not db:
            return render_template_string("""
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h2 style="color: red;">❌ Database Error</h2>
                <p>Unable to connect to database</p>
            </div>
            """), 500
        
        # Get ticket from Firebase
        ticket_ref = db.collection('tickets').document(ticket_id)
        ticket_doc = ticket_ref.get()
        
        if not ticket_doc.exists:
            return render_template_string("""
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h2 style="color: red;">❌ Invalid Ticket</h2>
                <p>This ticket does not exist</p>
            </div>
            """), 404
        
        ticket_data = ticket_doc.to_dict()
        
        if ticket_data.get('scanned', False):
            return render_template_string(f"""
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h2 style="color: orange;">⚠️ Already Used</h2>
                <p>This ticket has already been scanned</p>
                <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                    <h3>Ticket Details:</h3>
                    <p><strong>Name:</strong> {ticket_data.get('name', 'N/A')}</p>
                    <p><strong>Email:</strong> {ticket_data.get('email', 'N/A')}</p>
                    <p><strong>Originally scanned:</strong> {ticket_data.get('scanned_at', 'N/A')}</p>
                </div>
            </div>
            """)
        
        # Mark ticket as scanned
        ticket_ref.update({
            'scanned': True,
            'scanned_at': datetime.now()
        })
        
        return render_template_string(f"""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h1 style="color: green;">✅ Valid Ticket!</h1>
            <h2 style="color: #333; margin-top: 30px;">Welcome to ESYA Fest!</h2>
            
            <div style="margin: 30px auto; padding: 30px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border-radius: 15px; max-width: 400px;">
                <h3 style="margin-bottom: 20px;">🎫 Ticket Validated</h3>
                <p><strong>Name:</strong> {ticket_data.get('name', 'N/A')}</p>
                <p><strong>Email:</strong> {ticket_data.get('email', 'N/A')}</p>
                <p><strong>Entry Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div style="margin-top: 40px; padding: 20px; background: #d4edda; border-radius: 10px; border: 1px solid #c3e6cb;">
                <p style="color: #155724; font-size: 18px; font-weight: bold;">
                    🎉 Enjoy the fest! 🎉
                </p>
            </div>
        </div>
        """)
        
    except Exception as e:
        print(f"Validation error: {e}")
        return render_template_string("""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h2 style="color: red;">❌ Validation Error</h2>
            <p>Unable to validate ticket</p>
        </div>
        """), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'firebase_connected': db is not None,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)