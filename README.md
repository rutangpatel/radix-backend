# radix-backend

![License](https://img.shields.io/badge/license-Unlicense-green) ![Version](https://img.shields.io/badge/version-1.0.0-blue) ![Language](https://img.shields.io/badge/language-Python-yellow) ![Framework](https://img.shields.io/badge/framework-FastAPI-orange) ![GitHub](https://img.shields.io/badge/GitHub-rutangpatel/radix--backend-black?logo=github)

## 📋 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Tech Stack](#tech-stack)
- [Contributing](#contributing)

## ℹ️ Project Information

- **👤 Author:** rutangpatel
- **📦 Version:** 1.0.0
- **📄 License:** Unlicense
- **📂 Repository:** [https://github.com/rutangpatel/radix-backend](https://github.com/rutangpatel/radix-backend)
- **🏷️ Keywords:** fastapi mongodb biometrics face-recognition deepface vector-search jwt p2p-payments python imagekit rate-limiting bcrypt anti-spoofing facenet512 retinaface atomic-transactions rollback-system rest-api oauth2

## Features

- Three payment methods: PIN, mobile number, and face recognition
- Face enrollment using multiple images averaged into a single normalized embedding
- Anti-spoofing protection on all face recognition flows
- Atomic balance updates with overdraft prevention at the database level
- Automatic rollback and refund if a transaction fails mid-way
- JWT authentication with token blacklisting on logout and account changes
- bcrypt hashing for both passwords and PINs
- Rate limiting on all endpoints (stricter limits on payments and enrollment)
- Profile photo upload and management via ImageKit
- Monthly transaction history with IST timezone conversion
- Account deletion with full cascade: embeddings, profile photo, and active tokens

## Installation

1. Clone the repository
2. Create a virtual environment and install dependencies from requirements.txt
3. Set up a MongoDB Atlas cluster, create a Vector Search index on the `face_embeddings` collection with the following config:
   - Field: `deepface_embeddings`
   - Dimensions: `512`
   - Similarity: `cosine`
4. Add a `.env` file with `MONGO_DB_CONNECTION`, `SECRET_KEY`, and `IMAGEKIT_PRIVATE_KEY`
5. Run the server with: `uvicorn app.main_app:app --reload`

## Usage

1. Create an account via `POST /v1/users/signup`
2. Login via `POST /v1/auth/token` to get a JWT token
3. Enroll your face via `POST /v1/face/enroll` with 3-5 clear face images
4. Send money via `POST /v2/transaction/payment` (PIN), `/payment_using_mob_no` (mobile), or `POST /v1/face/pay` (face)
5. View transaction history via `GET /v2/transaction/history`

## Tech Stack

- **Backend:** FastAPI, PyMongo, MongoDB Atlas
- **ML:** DeepFace, Facenet512, RetinaFace, OpenCV
- **Auth:** python-jose (JWT), bcrypt, slowapi
- **Storage:** ImageKit

## Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change. Make sure to update tests and environment variables as needed.
