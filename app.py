import os
import cv2
import numpy as np
import torch
import mediapipe as mp
import uuid
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sklearn.metrics.pairwise import cosine_similarity
from facenet_pytorch import InceptionResnetV1, MTCNN
from database.database import user_DB
from recognition.recognition import extract_face, get_embedding, face_embedding
from recognition.liveness import BlinkLiveness

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
detector = MTCNN(keep_all=True, device=device)
model = InceptionResnetV1(pretrained="vggface2").eval().to(device)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False,
                                  max_num_faces=1,
                                  min_detection_confidence=0.5,
                                  min_tracking_confidence=0.5)

db = user_DB
users_data = db.get_all_users()

active_sessions = {}
blink_detector = BlinkLiveness()

blink_sessions = {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/user/add")
async def add_user(name: str = Form(...), file: UploadFile = Form(...)):
    img_bytes = await file.read()
    np_img = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    emb = face_embedding(frame, detector, model)
    if emb is None:
        return JSONResponse({"status": "failed", "msg": "No face detected"})
    
    user_id, best_score = "Unknown", -1
    for id, _, db_emb in users_data:
        score = cosine_similarity([emb], [db_emb])[0][0]
        if score > best_score:
            best_score = score
            user_id = id

    if best_score > 0.85:
        db.delete_user(user_id)

    db.add_user(name, emb)
    return JSONResponse({"status": "success", "msg": f"User '{name}' added"})

@app.post("/recognition")
async def recognition(file: UploadFile):
    img_bytes = await file.read()
    np_img = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    # Deteksi wajah
    boxes, _ = detector.detect(frame)
    if boxes is None or len(boxes) == 0:
        return JSONResponse({"status": "failed", "msg": "No face detected"})

    face = extract_face(frame, boxes[0])
    emb = get_embedding(face, model)

    user_id, best_score = "Unknown", -1
    for id, _, db_emb in users_data:
        score = cosine_similarity([emb], [db_emb])[0][0]
        if score > best_score:
            best_score = score
            user_id = id

    if best_score > 0.7:
        session_token = str(uuid.uuid4())
        active_sessions[session_token] = emb
        return JSONResponse({"status": "success", "user_id": user_id, "session_token": session_token})

    return JSONResponse({"status": "failed", "msg": "No match in database"})


@app.post("/liveness")
async def liveness(files: List[UploadFile], session_token: str = Form(...), user_id: int = Form(...)):
    if session_token not in active_sessions:
        return JSONResponse({"status": "failed", "msg": "Session not found"})

    if session_token not in blink_sessions:
        blink_sessions[session_token] = BlinkLiveness()

    blink_detector = blink_sessions[session_token]
    base_emb = active_sessions[session_token]
    live_detected = False

    for file in files:
        img_bytes = await file.read()
        np_img = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        boxes, _ = detector.detect(frame)
        if boxes is None or len(boxes) == 0:
            continue

        face = extract_face(frame, boxes[0])
        if face is None:
            return JSONResponse({"status": "failed", "msg": "Face not found"})

        emb = get_embedding(face, model)
        score = cosine_similarity([emb], [base_emb])[0][0]
        if score < 0.7:
            return JSONResponse({"status": "failed", "msg": "Face does not match recognition"})

        results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            live_detected = blink_detector.update(user_id, landmarks, frame.shape)

    if live_detected:
        return JSONResponse({"status": "success", "liveness": True})
    else:
        return JSONResponse({"status": "failed", "msg": "No blink detected"})


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8888)