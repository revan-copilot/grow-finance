
import sys
import os
from datetime import date, datetime
from decimal import Decimal

# Add the app directory to sys.path
sys.path.append(os.getcwd())

from db.database import SessionLocal, engine
from models.users import User
from models.clients import Client, Business, LoanApplication, ClientKyc
from models.loans import Loan
from core.security import get_password_hash
from core.emi import generate_repayment_schedule

def seed():
    db = SessionLocal()
    try:
        # 1. Ensure a staff user exists
        staff = db.query(User).filter(User.email == "staff@example.com").first()
        if not staff:
            staff = User(
                email="staff@example.com",
                full_name="Default Staff",
                role="staff",
                status="active",
                hashed_password=get_password_hash("staff123"),
                is_staff=True,
                is_active=True
            )
            db.add(staff)
            db.flush()
        
        # 2. Insert Sample Clients
        sample_clients = [
            {
                "full_name": "Ravi Kumar",
                "mobile_number": "9876543210",
                "status": "Active",
                "marital_status": "Married",
                "dob": date(1985, 5, 10),
                "resident_address": "123, Anna Salai, Chennai",
                "permanent_address": "123, Anna Salai, Chennai",
                "email": "ravi.kumar@example.com",
                "gender": "Male",
                "occupation": "Software Engineer"
            },
            {
                "full_name": "Priya Sharma",
                "mobile_number": "9123456780",
                "status": "Active",
                "marital_status": "Single",
                "dob": date(1992, 11, 22),
                "resident_address": "45, MG Road, Bangalore",
                "permanent_address": "45, MG Road, Bangalore",
                "email": "priya.sharma@example.com",
                "gender": "Female",
                "occupation": "Business Owner",
                "business": {
                    "name": "Priya's Boutique",
                    "ownership_type": "Sole Proprietorship",
                    "nature_of_business": "Retail",
                    "address": "45, MG Road, Bangalore",
                    "pincode": "560001",
                    "annual_turnover": Decimal("1500000.00"),
                    "business_start_date": date(2018, 1, 15)
                }
            },
            {
                "full_name": "Amit Patel",
                "mobile_number": "9988776655",
                "status": "Draft",
                "marital_status": "Married",
                "dob": date(1980, 3, 5),
                "resident_address": "Flat 202, Sunrise Apts, Mumbai",
                "permanent_address": "Sector 5, Gandhinagar, Gujarat",
                "email": "amit.patel@example.com",
            },
            {
                "full_name": "Anjali Gupta",
                "mobile_number": "8877665544",
                "status": "Active",
                "marital_status": "Married",
                "dob": date(1988, 8, 18),
                "resident_address": "12, Ring Road, Delhi",
                "permanent_address": "12, Ring Road, Delhi",
                "gender": "Female",
                "occupation": "Teacher",
                "loan_application": {
                    "loan_amount": Decimal("500000.00"),
                    "interest_rate": Decimal("12.00"),
                    "repayment_terms": "Monthly",
                    "total_months": 24,
                    "loan_start_date": date(2024, 1, 1),
                    "loan_collection_date": 5,
                    "purpose_of_loan": "Home Renovation",
                    "status": "Pending Approval"
                }
            }
        ]

        for client_data in sample_clients:
            existing = db.query(Client).filter(Client.mobile_number == client_data["mobile_number"]).first()
            if existing:
                print(f"Client {client_data['full_name']} already exists. Skipping.")
                continue
            
            # Extract nested data
            business_data = client_data.pop("business", None)
            loan_app_data = client_data.pop("loan_application", None)
            
            new_client = Client(
                **client_data,
                created_by_id=staff.id
            )
            db.add(new_client)
            db.flush()
            
            # Set custom ID
            new_client.client_custom_id = f"CL-{str(new_client.id).zfill(4)}"
            
            # Add KYC
            kyc = ClientKyc(
                client_id=new_client.id,
                kyc_status="Completed" if new_client.status == "Active" else "Pending"
            )
            db.add(kyc)
            
            if business_data:
                new_business = Business(
                    client_id=new_client.id,
                    **business_data
                )
                db.add(new_business)
            
            if loan_app_data:
                new_loan_app = LoanApplication(
                    client_id=new_client.id,
                    **loan_app_data
                )
                db.add(new_loan_app)
                db.flush()
                new_loan_app.loan_custom_id = f"LA-{str(new_loan_app.id).zfill(4)}"
                
                # If status is approved in seed, create the Loan record too
                if new_loan_app.status in ["Approved", "Active"]:
                     new_loan = Loan(
                        client_id=new_client.id,
                        loan_amount=new_loan_app.loan_amount,
                        interest_rate=new_loan_app.interest_rate,
                        commission_percentage=new_loan_app.commission_percentage or 0,
                        commission_amount=new_loan_app.commission_amount or 0,
                        cutting_fee=new_loan_app.cutting_fee or 0,
                        middle_man_name=new_loan_app.middle_man_name,
                        status="Active",
                        frequency=new_loan_app.repayment_terms,
                        tenure=new_loan_app.total_months,
                        emi_start_date=new_loan_app.loan_start_date,
                        collection_date=new_loan_app.loan_collection_date
                    )
                     db.add(new_loan)
                     db.flush()
                     new_loan.loan_custom_id = f"LN-{str(new_loan.id).zfill(4)}"
                     generate_repayment_schedule(db, new_loan)
            
            print(f"Inserted client: {new_client.full_name} ({new_client.client_custom_id})")
        
        db.commit()
        print("Seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
