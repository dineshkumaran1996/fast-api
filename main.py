from fastapi import FastAPI, Depends, HTTPException,APIRouter,status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm,HTTPBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt, JWTError
from datetime import timedelta,datetime

from models import User,Book, Base

# Create FastAPI app
app = FastAPI()

# Configure SQLAlchemy
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:kumaran1996@localhost/fastapi"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


# JWT Configuration
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
db = Session()
# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dependency for getting a database session
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
    
# User registration request model
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str
    
class BookCreate(BaseModel):
    title: str
    description: str
    author: str
    count: int

class BookUpdate(BaseModel):
    title: str
    description: str
    author: str
    count: int
  
#Create Api        
@app.post("/api/user/register", status_code=201)
def register(user: UserCreate):
    db = Session()
    # Check if username or email already exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username,email=user.email, password=hashed_password ,role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully"}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Generate access token
def create_access_token(data: dict):
    to_encode = data.copy()
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": datetime.utcnow() + expires_delta})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/api/user/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Verify user credentials
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

#Get current users
@app.get("/users/me")
def get_current_user(user: User = Depends(get_current_user)):
    return user


# Create Book API (Admin Only)
@app.post("/api/book")
def create_book(book_data: BookCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    book = Book(
        title=book_data.title,
        description=book_data.description,
        author=book_data.author,
        count=book_data.count
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return {"message": "Book created successfully"}



# Get All Books API
@app.get("/api/book")
def get_all_books(db: Session =Depends(get_db)):
    books = db.query(Book).all()
    return books


# Get Book API
@app.get("/api/book/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


# Update Book API (Admin Only)
@app.put("/api/book/{book_id}")
def update_book(book_id: int, book_update: BookUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
   
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book.title = book_update.title
    book.description = book_update.description
    book.author = book_update.author
    book.count = book_update.count
    db.commit()
    db.refresh(book)
    return {"message": "Book updated successfully"}

# Delete Book API (Admin Only)
@app.delete("/api/book/{book_id}")
def delete_book(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
      
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully"}

# Borrow Book API
@app.put("/api/book/{book_id}/borrow")
def borrow_book(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    num_borrowed_books = 0
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.count <= 0:
        raise HTTPException(status_code=409, detail="Book not available")
    
    book.count -= 1
    book.borrower_id = current_user.id  # Set the borrower_id to the current user's id
    db.commit()
    # Update the number of borrowed books
    num_borrowed_books += 1
    return {"message": "Book borrowed successfully", "num_borrowed_books": num_borrowed_books}

# @app.put("/api/book/{book_id}/borrow")
# def borrow_book(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
#     # Get the user's borrowing history from the database
#     user = db.query(User).filter(User.id == current_user.id).first()
#     if not user:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
#     # Define a variable to store the number of borrowed books
#     num_borrowed_books = user.num_borrowed_books or 0
    
#     book = db.query(Book).filter(Book.id == book_id).first()
#     if not book:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    
#     if book.count <= 0:
#         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book not available")
    
#     book.count -= 1
#     book.borrower_id = current_user.id  # Set the borrower_id to the current user's id
    
#     # Update the number of borrowed books
#     num_borrowed_books += 1
    
#     # Update the user's borrowing history in the database
#     user.borrowed_books_count = num_borrowed_books
#     db.commit()
    
#     return {"message": "Book borrowed successfully", "num_borrowed_books": num_borrowed_books}

# Return Book API
@app.put("/api/book/{book_id}/return")
def return_book(book_id: int,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book.count += 1 
    book.borrower_id = current_user.id
    book.borrower_id = None
    db.commit()
    return {"message": "Book returned successfully"}


# Get Books Borrowed by a User API
@app.get("/api/user/book")
def get_borrowed_books(email:str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    borrowed_books = db.query(Book).filter(Book.borrower_id == user.id).all()
    return borrowed_books

# Retrieve User/Book history API (Admin Only)
@app.get("/api/history")
def retrieve_history(email: str, book_title: str, type: str, date: str,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    query = db.query(Book)
    if email:
        query = query.filter(Book.borrower_email == email)
    if book_title:
        query = query.filter(Book.title == book_title)
    if type:
        query = query.filter(Book.type == type)
    if date:
        query = query.filter(Book.date == date)
    
    history = query.all()
    return history


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

