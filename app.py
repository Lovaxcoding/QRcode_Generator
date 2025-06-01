import customtkinter as ctk
from PIL import Image, ImageTk
import os
import cv2
import threading
import time
from pyzbar.pyzbar import decode

from func import generate_qr_code, read_qr_code_from_image

# --- Paramètres globaux de l'application ---
APP_NAME = "QRify - Générateur et Lecteur de QR Code"
APP_GEOMETRY = "900x650"
QR_CODE_PREVIEW_PATH = "temp_qr_preview.png"

# --- Police de caractères utilisée dans l'application ---
FONT_FAMILY = "Roboto" 

class QRCodeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry(APP_GEOMETRY)
        self.resizable(False, False)
        

        # --- Configuration du thème ---
        ctk.set_appearance_mode("Dark")  # "Light", "Dark", "System"
        ctk.set_default_color_theme("green")

        # --- Chargement des polices ---
        self.font_title = ctk.CTkFont(family=FONT_FAMILY, size=32, weight="bold")
        self.font_heading = ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold")
        self.font_label = ctk.CTkFont(family=FONT_FAMILY, size=15)
        self.font_button = ctk.CTkFont(family=FONT_FAMILY, size=18, weight="normal")
        self.font_entry = ctk.CTkFont(family=FONT_FAMILY, size=16)
        self.font_status = ctk.CTkFont(family=FONT_FAMILY, size=13, slant="italic")


        # --- Variables pour la webcam ---
        self.cap = None
        self.is_scanning = False
        self.webcam_thread = None

        # --- Configuration de la grille principale ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Onglets pour Génération et Lecture (avec style) ---
        self.tabview = ctk.CTkTabview(self,
                                      corner_radius=10,
                                      segmented_button_fg_color=("gray80", "gray20"),
                                      segmented_button_selected_color=("green", "darkgreen"))
        self.tabview.grid(row=0, column=0, padx=25, pady=25, sticky="nsew")

        self.tabview.add("Génération de QR Code")
        self.tabview.add("Lecture de QR Code")

        # --- Configuration de la grille pour l'onglet "Génération" ---
        gen_tab = self.tabview.tab("Génération de QR Code")
        gen_tab.grid_columnconfigure((0, 1), weight=1)
        gen_tab.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        # --- Configuration de la grille pour l'onglet "Lecture" ---
        read_tab = self.tabview.tab("Lecture de QR Code")
        read_tab.grid_columnconfigure((0, 1), weight=1)
        read_tab.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        self.create_generation_tab()
        self.create_reading_tab()

    def create_generation_tab(self):
        gen_tab = self.tabview.tab("Génération de QR Code")

        ctk.CTkLabel(gen_tab, text="Créez votre QR Code", font=self.font_heading).grid(row=0, column=0, columnspan=2, pady=(20, 10))

        ctk.CTkLabel(gen_tab, text="Données à encoder :", font=self.font_label).grid(row=1, column=0, sticky="e", padx=(10,5))
        self.data_entry = ctk.CTkEntry(gen_tab, width=400, height=35,
                                       placeholder_text="URL, texte, contact...",
                                       font=self.font_entry,
                                       corner_radius=8)
        self.data_entry.grid(row=1, column=1, sticky="w", padx=(5,10))

        size_frame = ctk.CTkFrame(gen_tab, fg_color="transparent")
        size_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew", padx=50)
        size_frame.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkLabel(size_frame, text="Niveau de détail :", font=self.font_label).grid(row=0, column=0, sticky="e", padx=(10,5))
        self.size_slider = ctk.CTkSlider(size_frame, from_=5, to=20, number_of_steps=15,
                                         command=self.update_qr_size_label,
                                         button_corner_radius=10,
                                         fg_color=("gray70", "gray30"))
        self.size_slider.set(10)
        self.size_slider.grid(row=0, column=1, sticky="ew", padx=5)
        self.qr_size_label_val = ctk.CTkLabel(size_frame, text="10", font=self.font_label)
        self.qr_size_label_val.grid(row=0, column=2, sticky="w", padx=(5,10))

        self.generate_button = ctk.CTkButton(gen_tab, text="Générer QR Code", command=self.on_generate_qr,
                                             font=self.font_button, height=45, corner_radius=10)
        self.generate_button.grid(row=3, column=0, columnspan=2, pady=25)

        self.qr_image_label = ctk.CTkLabel(gen_tab, text="QR Code non généré", font=self.font_label,
                                           text_color="gray", image=None, compound="top")
        self.qr_image_label.grid(row=4, column=0, columnspan=2, pady=10)

        self.save_qr_button = ctk.CTkButton(gen_tab, text="Enregistrer l'image", command=self.save_qr_code_image,
                                            font=self.font_button, height=35, corner_radius=8,
                                            fg_color="gray", hover_color="darkgray")
        self.save_qr_button.grid(row=5, column=0, columnspan=2, pady=10)
        self.save_qr_button.grid_remove()

        self.gen_status_label = ctk.CTkLabel(gen_tab, text="", font=self.font_status, text_color="green")
        self.gen_status_label.grid(row=6, column=0, columnspan=2, pady=(0, 20))

    def create_reading_tab(self):
        read_tab = self.tabview.tab("Lecture de QR Code")

        ctk.CTkLabel(read_tab, text="Scannez un QR Code", font=self.font_heading).grid(row=0, column=0, columnspan=2, pady=(20, 10))

        scan_buttons_frame = ctk.CTkFrame(read_tab, fg_color="transparent")
        scan_buttons_frame.grid(row=1, column=0, columnspan=2, pady=15, sticky="ew", padx=50)
        scan_buttons_frame.grid_columnconfigure((0,1), weight=1)

        self.scan_webcam_button = ctk.CTkButton(scan_buttons_frame, text="Scanner via Webcam", command=self.toggle_webcam_scan,
                                                font=self.font_button, height=40, corner_radius=10)
        self.scan_webcam_button.grid(row=0, column=0, pady=5, padx=10, sticky="ew")

        self.scan_image_button = ctk.CTkButton(scan_buttons_frame, text="Scanner depuis une Image", command=self.on_scan_from_image,
                                               font=self.font_button, height=40, corner_radius=10)
        self.scan_image_button.grid(row=0, column=1, pady=5, padx=10, sticky="ew")

        self.webcam_frame = ctk.CTkFrame(read_tab, width=520, height=380, corner_radius=15)
        self.webcam_frame.grid(row=2, column=0, columnspan=2, pady=15)
        self.webcam_frame.grid_propagate(False)

        self.webcam_label = ctk.CTkLabel(self.webcam_frame, text="Cliquez sur 'Scanner via Webcam' pour démarrer",
                                         font=self.font_label, text_color="gray")
        self.webcam_label.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(read_tab, text="Données décodées :", font=self.font_label).grid(row=3, column=0, sticky="e", padx=(10,5))
        self.decoded_data_entry = ctk.CTkEntry(read_tab, width=450, height=35,
                                               placeholder_text="Le QR code décodé apparaîtra ici...",
                                               font=self.font_entry,
                                               corner_radius=8,
                                               state="readonly")
        self.decoded_data_entry.grid(row=3, column=1, sticky="w", padx=(5,10))

        self.copy_decoded_button = ctk.CTkButton(read_tab, text="Copier Résultat", command=self.copy_decoded_data,
                                                 font=self.font_button, height=35, corner_radius=8,
                                                 fg_color="gray", hover_color="darkgray")
        self.copy_decoded_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.read_status_label = ctk.CTkLabel(read_tab, text="", font=self.font_status, text_color="green")
        self.read_status_label.grid(row=5, column=0, columnspan=2, pady=(0, 20))

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_qr_size_label(self, value):
        self.qr_size_label_val.configure(text=f"{int(value)}")

    def on_generate_qr(self):
        data = self.data_entry.get()
        qr_size = int(self.size_slider.get())

        if not data:
            self.gen_status_label.configure(text="Veuillez entrer des données à encoder !", text_color="red")
            self.save_qr_button.grid_remove()
            self.qr_image_label.configure(image=None, text="QR Code non généré")
            return

        if generate_qr_code(data, QR_CODE_PREVIEW_PATH, size=qr_size):
            try:
                img_pil = Image.open(QR_CODE_PREVIEW_PATH)
                img_pil = img_pil.resize((250, 250), Image.LANCZOS)
                img_ctk = ImageTk.PhotoImage(img_pil)

                self.qr_image_label.configure(image=img_ctk, text="")
                self.qr_image_label.image = img_ctk
                self.save_qr_button.grid()

                self.gen_status_label.configure(text="QR Code généré avec succès !", text_color="green")
                self.after(2000, lambda: self.gen_status_label.configure(text=""))
            except Exception as e:
                self.gen_status_label.configure(text=f"Erreur d'affichage : {e}", text_color="red")
                self.save_qr_button.grid_remove()
                self.qr_image_label.configure(image=None, text="Erreur lors de l'affichage")
        else:
            self.gen_status_label.configure(text="Échec de la génération du QR Code.", text_color="red")
            self.save_qr_button.grid_remove()
            self.qr_image_label.configure(image=None, text="Échec de la génération")

    def save_qr_code_image(self):
        if not os.path.exists(QR_CODE_PREVIEW_PATH):
            self.gen_status_label.configure(text="Aucun QR Code à enregistrer.", text_color="red")
            return

        file_path = ctk.filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            title="Enregistrer le QR Code sous..."
        )
        if file_path:
            try:
                Image.open(QR_CODE_PREVIEW_PATH).save(file_path)
                self.gen_status_label.configure(text=f"QR Code enregistré : {os.path.basename(file_path)}", text_color="blue")
                self.after(2000, lambda: self.gen_status_label.configure(text=""))
            except Exception as e:
                self.gen_status_label.configure(text=f"Erreur lors de l'enregistrement : {e}", text_color="red")

    def toggle_webcam_scan(self):
        if self.is_scanning:
            self.is_scanning = False
            self.scan_webcam_button.configure(text="Scanner via Webcam", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            self.webcam_label.configure(image=None, text="Webcam éteinte")
            if self.cap:
                self.cap.release()
            self.read_status_label.configure(text="Scan webcam arrêté.", text_color="orange")
            self.decoded_data_entry.delete(0, ctk.END)
            self.decoded_data_entry.insert(0, "")
            self.decoded_data_entry.configure(state="readonly")
        else:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.read_status_label.configure(text="Impossible d'ouvrir la webcam. Vérifiez les permissions ou si elle est en usage.", text_color="red")
                return

            self.is_scanning = True
            self.scan_webcam_button.configure(text="Arrêter le Scan Webcam", fg_color="red", hover_color="darkred")
            self.read_status_label.configure(text="Webcam active. Scanning...", text_color="blue")
            self.webcam_thread = threading.Thread(target=self.webcam_scan_loop, daemon=True)
            self.webcam_thread.start()
            self.decoded_data_entry.configure(state="normal")

    def webcam_scan_loop(self):
        while self.is_scanning:
            ret, frame = self.cap.read()
            if not ret:
                self.is_scanning = False
                self.after(0, lambda: self.read_status_label.configure(text="Webcam déconnectée ou erreur de flux.", text_color="red"))
                self.after(0, lambda: self.toggle_webcam_scan())
                break

            decoded_objects = decode(frame)
            if decoded_objects:
                decoded_data = decoded_objects[0].data.decode('utf-8')
                self.decoded_data_entry.delete(0, ctk.END)
                self.decoded_data_entry.insert(0, decoded_data)
                self.read_status_label.configure(text=f"QR Code détecté ! Données: {decoded_data[:30]}...", text_color="green")

            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_pil = img_pil.resize((int(self.webcam_frame.winfo_width() * 0.95), int(self.webcam_frame.winfo_height() * 0.95)), Image.LANCZOS)
            img_ctk = ImageTk.PhotoImage(img_pil)

            self.webcam_label.configure(image=img_ctk)
            self.webcam_label.image = img_ctk

            time.sleep(0.01)

        if self.cap:
            self.cap.release()
        if not self.is_scanning:
            self.after(0, lambda: self.webcam_label.configure(text="Webcam inactive."))


    def on_scan_from_image(self):
        if self.is_scanning:
            self.toggle_webcam_scan()

        file_path = ctk.filedialog.askopenfilename(
            title="Sélectionner une image de QR Code",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.read_status_label.configure(text="Lecture de l'image...", text_color="blue")
            self.decoded_data_entry.configure(state="normal")
            self.decoded_data_entry.delete(0, ctk.END)

            decoded_data = read_qr_code_from_image(file_path)

            if decoded_data:
                self.decoded_data_entry.insert(0, decoded_data)
                self.read_status_label.configure(text="QR Code lu avec succès !", text_color="green")
            else:
                self.read_status_label.configure(text="Aucun QR Code trouvé dans l'image ou erreur de lecture.", text_color="red")

            self.decoded_data_entry.configure(state="readonly")
            self.after(2000, lambda: self.read_status_label.configure(text=""))


    def copy_decoded_data(self):
        decoded_text = self.decoded_data_entry.get()
        if decoded_text:
            self.clipboard_clear()
            self.clipboard_append(decoded_text)
            self.read_status_label.configure(text="Données copiées dans le presse-papiers !", text_color="blue")
            self.after(1500, lambda: self.read_status_label.configure(text=""))
        else:
            self.read_status_label.configure(text="Aucune donnée à copier.", text_color="red")


    def on_closing(self):
        if self.is_scanning:
            self.is_scanning = False
            if self.webcam_thread and self.webcam_thread.is_alive():
                self.webcam_thread.join(timeout=0.5)
        if self.cap:
            self.cap.release()
        if os.path.exists(QR_CODE_PREVIEW_PATH):
            os.remove(QR_CODE_PREVIEW_PATH)
        self.destroy()

if __name__ == "__main__":
    app = QRCodeApp()
    app.mainloop()