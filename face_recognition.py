import cv2
import torch
from sklearn.metrics.pairwise import cosine_similarity
from facenet_pytorch import InceptionResnetV1, MTCNN
from database.database import user_DB
from recognition.recognition import extract_face, get_embedding, face_embedding

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
detector = MTCNN(keep_all=True, device=device)
model = InceptionResnetV1(pretrained="vggface2").eval().to(device)

def recognize_realtime(db, threshold=0.7):
    cap = cv2.VideoCapture(0)
    print("Start camera... press 'q' to exit")

    users_data = db.get_all_users()
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
            for box in boxes:
                box_scaled = [int(b * scale) for b, scale in zip(box, [scale_x, scale_y, scale_x, scale_y])]
                face = extract_face(frame, box_scaled)
                if face is None:
                    continue
                try:
                    emb = get_embedding(face, model)
                except RuntimeError as e:
                    print(f"WARNING Embedding error: {e}")
                    continue

                best_match, best_score = "Unknown", -1
                for _, name, db_emb in users_data:
                    score = cosine_similarity([emb], [db_emb])[0][0]
                    if score > best_score:
                        best_score = score
                        best_match = name

                if best_score < threshold:
                    best_match, best_score = "Unknown", 0

                x1, y1, x2, y2 = box_scaled
                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
                cv2.putText(frame, f"{best_match} ({best_score:.2f})",
                            (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

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