import cv2
import numpy as np
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def clahe_eq(face):
    lab = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l_clahe = clahe.apply(l)
    lab_clahe = cv2.merge((l_clahe, a, b))
    face_clahe = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
    return face_clahe

def extract_face(image, box):
    x1, y1, x2, y2 = [int(b) for b in box]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
    face = image[y1:y2, x1:x2]
    if face.shape[0] < 20 or face.shape[1] < 20:
        return None
    face = cv2.resize(face, (160,160))
    face = clahe_eq(face)
    face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
    return face

def get_embedding(face_img, model):
    face_tensor = torch.tensor(face_img.transpose(2,0,1)).unsqueeze(0).float()
    face_tensor = (face_tensor - 127.5) / 128.0
    face_tensor = face_tensor.to(device)
    with torch.no_grad():
        emb = model(face_tensor).cpu().numpy()[0]
    emb = emb / np.linalg.norm(emb)
    return emb

def face_embedding(img, detector, model):
    if isinstance(img, str):
        image = cv2.imread(img)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        image = img
    boxes, _ = detector.detect(image)
    if boxes is None or len(boxes) == 0:
        print(f"No face on {img}")
        return
    box = boxes[0]
    face = extract_face(image, box)
    emb = get_embedding(face, model)

    return emb