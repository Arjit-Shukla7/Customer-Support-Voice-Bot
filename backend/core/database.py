from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
from datetime import datetime, timezone

# Define the Patient Table
class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    phone_number: Optional[str] = None
    medical_history: str  
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Define the Call Record Table
class CallRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    transcript: str       
    summary: Optional[str] = None  
    sentiment: Optional[str] = None 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Setup the SQLite Engine
sqlite_file_name = "healthcare.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# --- ISOLATED TEST & SEED SCRIPT ---
if __name__ == "__main__":
    print("🧱 Building the Memory Bank...")
    create_db_and_tables()
    
    # Diverse Patients to test the AI's adaptability
    seed_patients = [
        Patient(
            name="John Doe",
            phone_number="+15551234567",
            medical_history="Patient had a lower left molar extraction (wisdom tooth) yesterday. Might be experiencing mild swelling and pain. Prescribed Ibuprofen."
        ),
        Patient(
            name="Sarah Connor",
            phone_number="+15559876543",
            medical_history="Patient had ACL reconstruction surgery on her right knee 3 days ago. Check for excessive stiffness and remind her to do her daily physical therapy stretches."
        ),
        Patient(
            name="Michael Scott",
            phone_number="+15554567890",
            medical_history="Routine annual checkup last week showed mild hypertension (high blood pressure). Prescribed Lisinopril. Check if he picked up his medication and if he feels any dizziness."
        ),
        Patient(
            name="Emily Chen",
            phone_number="+15557890123",
            medical_history="Patient had a root canal on an upper right bicuspid yesterday. Might have sensitivity to hot or cold. Currently taking Amoxicillin to prevent infection."
        ),
        Patient(
            name="David Wallace",
            phone_number="+15552345678",
            medical_history="Patient visited the clinic for chronic lower back pain. MRI results are still pending. Check on his current pain levels and remind him to avoid heavy lifting."
        )
    ]
    
    with Session(engine) as session:
        # Check if we already seeded the database
        existing_patients = session.exec(select(Patient)).all()
        
        if len(existing_patients) == 0:
            for patient in seed_patients:
                session.add(patient)
            session.commit()
            print(f"✅ Successfully seeded {len(seed_patients)} new patients into the database!")
        else:
            print(f"✅ Database is already populated with {len(existing_patients)} patients.")
            for p in existing_patients:
                print(f"   - {p.id}: {p.name}")
            
    print("✅ Database setup complete! 'healthcare.db' is ready.")