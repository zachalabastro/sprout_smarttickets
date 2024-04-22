import streamlit as st # Streamlit version 1.24.0 was used
import os
from PIL import Image, ImageEnhance
import pytesseract
import cv2
import numpy as np
import time

upload_dir = "/Users/zachalabastro/Desktop/[SPROUT] Azure Deployment/file_upload" # Replace accordingly
output_dir = "/Users/zachalabastro/Desktop/[SPROUT] Azure Deployment/file_output" # Replace accordingly
output_file = "/Users/zachalabastro/Desktop/[SPROUT] Azure Deployment/file_output/final_output.txt" # Replace accordingly
os.makedirs(upload_dir, exist_ok=True)

# File upload
file_label = "Upload JPG or PDF files"
uploaded_files = st.file_uploader(file_label, type=["jpg", "pdf"], accept_multiple_files=True)

if st.button("Upload Files"):
    files = os.listdir(upload_dir)
    for file in files:
            os.remove(os.path.join(upload_dir, file))

    outputs = os.listdir(output_dir)
    for output in outputs:
         os.remove(os.path.join(output_dir, output))

    if not uploaded_files:
        warning = st.warning("No files were selected. Please select at least one file.")
        time.sleep(3)
        warning.empty()
    else:
        for uploaded_file in uploaded_files:
            with open(os.path.join(upload_dir, uploaded_file.name), "wb") as f:
                f.write(uploaded_file.read())
            success = st.success(f"File '{uploaded_file.name}' has been uploaded successfully.")

    # Process each uploaded image
    for i, uploaded_file in enumerate(uploaded_files, start=1):
        pil_image = Image.open(uploaded_file)
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced_image = enhancer.enhance(2.0)
        gray_image = enhanced_image.convert('L')
        opencv_image = cv2.cvtColor(np.array(gray_image), cv2.COLOR_RGB2BGR)
        threshold_image = cv2.adaptiveThreshold(
            src=cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY),
            maxValue=255,
            adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresholdType=cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )

        # Perform OCR using Tesseract
        text = pytesseract.image_to_string(threshold_image)

        # Save processed image
        output_image_path = f'/Users/zachalabastro/Desktop/[SPROUT] Azure Deployment/file_output/upload_{i}.jpg'
        cv2.imwrite(output_image_path, threshold_image)

        # Save extracted text
        with open(f'/Users/zachalabastro/Desktop/[SPROUT] Azure Deployment/file_output/upload_text_{i}.txt', 'w') as file:
            file.write(text)

with open(output_file, 'a') as output:
    for filename in os.listdir(output_dir):
        if filename.endswith('.txt'):
            with open(os.path.join(output_dir, filename), 'r') as file:
                file_contents = file.read()
            output.write(file_contents + '\n---\n')