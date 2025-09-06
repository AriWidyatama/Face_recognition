import pickle
import datetime
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    embedding = Column(LargeBinary, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

class UserDB:
    def __init__(self, connection, connector, username, password, host, port, db_name):
        db_url=f"{connection}+{connector}://{username}:{password}@{host}:{port}/{db_name}"
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def add_user(self, name, embedding):
        session = self.Session()
        emb_blob = pickle.dumps(embedding)
        user = User(name=name, embedding=emb_blob)
        session.add(user)
        session.commit()
        session.close()
        print(f"User '{name}' added successfully.")

    def get_all_users(self):
        session = self.Session()
        users = session.query(User).all()
        session.close()
        return [(u.id, u.name, pickle.loads(u.embedding)) for u in users]

    def get_user_by_name(self, name):
        session = self.Session()
        user = session.query(User).filter_by(name=name).first()
        session.close()
        if user:
            return pickle.loads(user.embedding)
        return None
    
    def get_user_by_id(self, id):
        session = self.Session()
        user = session.query(User).filter_by(id=id).first()
        session.close()
        if user:
            return pickle.loads(user.embedding)
        return None

    def delete_user(self, id):
        session = self.Session()
        user = session.query(User).filter_by(id=id).first()
        if user:
            session.delete(user)
            session.commit()
            print(f"User '{id}' delete successfully.")
        session.close()
