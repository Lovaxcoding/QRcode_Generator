import qrcode
from PIL import Image # Nécessaire pour qrcode et pour la manipulation d'images
import cv2 # Pour la lecture de QR code via webcam ou image
from pyzbar.pyzbar import decode # Pour décoder le QR code

def generate_qr_code(data, file_path="qrcode.png", size=8, border=2):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        img.save(file_path)
        return True
    except Exception as e:
        print(f"Erreur lors de la génération du QR code : {e}")
        return False

def read_qr_code_from_image(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"L'image n'a pas pu être chargée : {image_path}")

        decoded_objects = decode(img)
        if decoded_objects:
            return decoded_objects[0].data.decode('utf-8')
        else:
            return None
    except Exception as e:
        print(f"Erreur lors de la lecture du QR code depuis l'image : {e}")
        return None

