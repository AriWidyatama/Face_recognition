import cv2
import torch
import mediapipe as mp
from sklearn.metrics.pairwise import cosine_similarity
from facenet_pytorch import InceptionResnetV1, MTCNN
from collections import deque
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

def recognize_realtime(db, threshold=0.7):
    cap = cv2.VideoCapture(0)
    print("Start camera... press 'q' to exit")

    users_data = db.get_all_users()
    blink_detector = BlinkLiveness()

    face_states = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        small_frame = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)
        boxes, _ = detector.detect(small_frame)

        if boxes is not None:
            scale_x = frame.shape[1] / small_frame.shape[1]
            scale_y = frame.shape[0] / small_frame.shape[0]
            for i, box in enumerate(boxes):
                box_scaled = [int(b * scale) for b, scale in zip(box, [scale_x, scale_y, scale_x, scale_y])]
                face = extract_face(frame, box_scaled)
                if face is None:
                    continue

                try:
                    emb = get_embedding(face, model)
                except RuntimeError:
                    continue

                best_match, best_score = "Unknown", -1
                for _, name, db_emb in users_data:
                    score = cosine_similarity([emb], [db_emb])[0][0]
                    if score > best_score:
                        best_score = score
                        best_match = name
                if best_score < threshold:
                    best_match = "Unknown"

                if i not in face_states or face_states[i]["name"] != best_match:
                    face_states[i] = {"name": best_match, "live": False}
                    blink_detector.blink_counters[i] = 0
                    blink_detector.blink_history[i] = deque(maxlen=blink_detector.window_size)

                is_live = True
                if best_match != "Unknown":
                    results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    if results.multi_face_landmarks:
                        landmarks = results.multi_face_landmarks[i].landmark
                        is_live = blink_detector.update(i, landmarks, frame.shape)
                    if not is_live:
                        best_match = "Blink Your Eyes Slowly!"

                x1, y1, x2, y2 = box_scaled
                if best_match == "Unknown":
                    color = (0, 0, 255)
                elif is_live:
                    color = (0,255,0)
                else:
                    color = (0,255,255)
                cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
                cv2.putText(frame, f"{best_match} ({best_score:.2f})",
                            (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        for fid in list(face_states.keys()):
            if boxes is not None:
                max_faces = len(boxes)
            else:
                max_faces = 0

            if fid >= max_faces:
                face_states[fid]["lost_frames"] = face_states[fid].get("lost_frames", 0) + 1
                if face_states[fid]["lost_frames"] > 25:
                    del face_states[fid]

        cv2.imshow("Face Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    db = user_DB

    #add users data ⬇️
    #db.add_user("Name", face_embedding("Path Image", detector, model))

    if not db.get_all_users():
        db.add_user("Budi", face_embedding("image/foto1.jpeg", detector, model))

    recognize_realtime(db, threshold=0.7)