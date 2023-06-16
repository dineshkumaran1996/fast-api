from sqlalchemy import Column, Integer, String,ForeignKey
from sqlalchemy.orm import declarative_base,relationship

Base = declarative_base()

# User model    
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)

    borrowed_books = relationship("Book", back_populates="borrower")
    
# Book Model
class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    author = Column(String)
    count = Column(Integer)
    borrower_id = Column(Integer, ForeignKey("users.id"))

    borrower = relationship("User", back_populates="borrowed_books")