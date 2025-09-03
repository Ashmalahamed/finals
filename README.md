#  CropSight AI – Rice Leaf Disease Detection System

A web-based AI-powered system to help Sri Lankan paddy farmers detect common rice leaf diseases using only a smartphone. Built with **Flask, TensorFlow, and Computer Vision**, this system enables early disease detection to reduce crop loss and improve yield.



##  Project Overview

CropSight AI is a **practical, accessible, and multilingual** solution for rice disease detection. It allows farmers to:
- Upload a photo of a rice leaf
- Get instant diagnosis of diseases like **Brown Spot, Hispa, and Leaf Blast**
- View results with confidence scores
- Access history in **Sri Lankan time (Asia/Colombo)**

The system includes:
-  User dashboard with Sinhala, Tamil, and English support
-  Admin panel for user management and monitoring
-  Secure login/signup with Gmail validation
-  Prediction history with correct time zone formatting
-  Lightweight CNN model for high-accuracy classification

>  **Note**: This project focuses on **image-based disease detection only** — no weather or harvest prediction is used, due to the unavailability of `meteo.gov.lk`.

---





##  Technology Stack

| Layer | Technology |
|------|-----------|
| **Frontend** | HTML5, CSS3, JavaScript |
| **Backend** | Python, Flask |
| **Database** | SQLite3 |
| **AI Model** | TensorFlow/Keras (CNN) |
| **Security** | `werkzeug.security` (password hashing) |
| **Hosting** | Flask Dev Server (can be deployed to cloud) |

---

##  Model Accuracy

- **Dataset**: Custom rice leaf dataset (Brown Spot, Hispa, Leaf Blast, Healthy)
- **Model**: Convolutional Neural Network (CNN)
- **Accuracy**: >94% on validation set
- **Image Size**: 150×150 pixels
- **Classes**: `BrownSpot`, `Hispa`, `LeafBlast`, `Healthy`

> Model files: `models/rice_disease_model.h5`, `models/class_names.npy`



