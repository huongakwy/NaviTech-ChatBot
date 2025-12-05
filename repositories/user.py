import uuid
from sqlalchemy.orm import Session
from models.user import UserCreateModel, UserTable, UserModel
from db import Session

class UserRespository():
    @staticmethod
    def create(payload: UserCreateModel) -> UserModel:
        with Session() as session:
            user = UserTable(**payload.model_dump())
            session.add(user)
            session.commit()
            session.refresh(user)
            return UserModel.model_validate(user)

    @staticmethod
    def get(payload: uuid.UUID) -> UserModel:
        with Session() as session:
            user = session.query(UserTable).filter(UserTable.id == payload).first()
            if user:
                return UserModel.model_validate(user)
            return UserModel(id=payload, first_name='sample', last_name='sample', email='sample', phone_number='sample', password='sample', role_id=1, is_active=True, is_verified=True, is_deleted=False)
        
    @staticmethod
    def update(id: uuid.UUID, data: UserCreateModel):
        with Session() as session:
            user = session.query(UserTable).filter(UserTable.id == id).first()
            if not user:
                return None
            for key, value in data.model_dump().items():
                setattr(user, key, value)
            session.commit()
            session.refresh(user)
            return UserModel.model_validate(user)
        
    @staticmethod
    def delete(payload: uuid.UUID):
        with Session() as session:
            user = session.query(UserTable).filter(UserTable.id == payload).first()
            if user:
                session.delete(user)
                session.commit()
            return user
        
    @staticmethod
    def get_all_user():
        with Session() as session:
            users = session.query(UserTable).all()
            return [UserModel.model_validate(user) for user in users]    
