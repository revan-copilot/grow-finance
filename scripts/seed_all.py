
import sys
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

# Add the app directory to sys.path
sys.path.append(os.getcwd())

from db.database import SessionLocal
from models.users import User
from models.clients import Client, Business, ClientKyc
from models.loans import Loan
from models.transactions import Transaction, RepaymentSchedule
from core.security import get_password_hash
from core.emi import generate_repayment_schedule

def seed_all():
    db = SessionLocal()
    try:
        # 1. Seed Users (20+)
        print("Seeding Users...")
        staff_users = []
        customer_users = []
        
        # Ensure at least 1 admin and 1 staff
        existing_admin = db.query(User).filter(User.role == "admin").first()
        if not existing_admin:
            admin_user = User(
                email="admin@growfinance.com",
                full_name="System Admin",
                first_name="Grow",
                last_name="Admin",
                role="admin",
                status="active",
                hashed_password=get_password_hash("admin123"),
                is_superuser=True,
                is_active=True
            )
            db.add(admin_user)
            db.flush()
        
        for i in range(1, 11):
            email = f"staff{i}@growfinance.com"
            if not db.query(User).filter(User.email == email).first():
                user = User(
                    email=email,
                    full_name=f"Staff Member {i}",
                    first_name="Finance",
                    last_name=f"Staff {i}",
                    role="staff",
                    status="active",
                    phone_number=f"98765432{i:02d}",
                    job_title="Finance Officer",
                    hashed_password=get_password_hash("staff123"),
                    is_staff=True,
                    is_active=True
                )
                db.add(user)
                staff_users.append(user)
        
        for i in range(1, 21):
            email = f"customer{i}@example.com"
            if not db.query(User).filter(User.email == email).first():
                user = User(
                    email=email,
                    full_name=f"Customer Name {i}",
                    first_name="Client",
                    last_name=f"User {i}",
                    role="customer",
                    status="active",
                    phone_number=f"91234567{i:02d}",
                    hashed_password=get_password_hash("customer123"),
                    is_active=True
                )
                db.add(user)
                customer_users.append(user)
        
        db.flush()
        print(f"Users seeded. Total users: {db.query(User).count()}")

        # 2. Seed Clients (20+)
        print("Seeding Clients...")
        # Get one staff to use as creator
        staff = db.query(User).filter(User.role == "staff").first()
        
        clients = []
        for i in range(1, 31):
            mobile = f"90000000{i:02d}"
            existing_client = db.query(Client).filter(Client.mobile_number == mobile).first()
            if not existing_client:
                # Assign to a customer user if available
                user_id = customer_users[i-1].id if i <= len(customer_users) else None
                
                client = Client(
                    full_name=f"Client User {i}",
                    mobile_number=mobile,
                    email=f"client{i}@example.com",
                    status="Active",
                    marital_status=random.choice(["Single", "Married", "Divorced"]),
                    dob=date(1970 + random.randint(0, 30), random.randint(1, 12), random.randint(1, 28)),
                    gender=random.choice(["Male", "Female", "Other"]),
                    occupation=random.choice(["Engineer", "Doctor", "Teacher", "Business", "Student"]),
                    resident_address=f"Street {i}, City {random.randint(1, 5)}, State",
                    permanent_address=f"Street {i}, City {random.randint(1, 5)}, State",
                    created_by_id=staff.id,
                    user_id=user_id
                )
                db.add(client)
                db.flush()
                client.client_custom_id = f"CL-{str(client.id).zfill(4)}"
                
                # Add KYC
                kyc = ClientKyc(client_id=client.id, kyc_status="Completed")
                db.add(kyc)
                
                # Add Business for some
                if i % 2 == 0:
                    biz = Business(
                        client_id=client.id,
                        name=f"Business {i} Ltd",
                        ownership_type="Sole Proprietorship",
                        nature_of_business="Retail",
                        address=client.resident_address,
                        pincode="600001",
                        annual_turnover=Decimal(random.randint(500000, 5000000)),
                        business_start_date=date(2010, 1, 1)
                    )
                    db.add(biz)
                
                if user_id:
                    client.user_id = user_id
                
                clients.append(client)
            else:
                clients.append(existing_client)
        
        db.flush()
        print(f"Clients seeded. Total clients: {db.query(Client).count()}")

        if not clients:
            clients = db.query(Client).all()

        # Update existing users with first/last names if missing
        all_users = db.query(User).all()
        for u in all_users:
            if not u.first_name:
                u.first_name = u.full_name.split()[0]
                u.last_name = u.full_name.split()[-1] if len(u.full_name.split()) > 1 else ""
        
        db.flush()

        # 3. Seed Loans (20+ across clients)
        print("Seeding Loans...")
        loans = []
        for i in range(1, 26):
            client = random.choice(clients)
            loan_amount = Decimal(random.randint(50000, 1000000))
            
            loan = Loan(
                client_id=client.id,
                loan_amount=loan_amount,
                interest_rate=Decimal(random.randint(10, 24)),
                commission_percentage=Decimal("2.00"),
                commission_amount=loan_amount * Decimal("0.02"),
                cutting_fee=Decimal("1000.00"),
                status="Active" if i <= 20 else "Pending",
                frequency="Monthly",
                tenure=random.choice([12, 24, 36]),
                emi_start_date=date.today() - timedelta(days=random.randint(0, 180)),
                collection_date=random.randint(1, 28)
            )
            db.add(loan)
            db.flush()
            loan.loan_custom_id = f"LN-{str(loan.id).zfill(4)}"
            
            if loan.status == "Active":
                generate_repayment_schedule(db, loan)
            
            loans.append(loan)
            
        db.flush()
        print(f"Loans seeded. Total loans: {db.query(Loan).count()}")

        # 4. Seed Transactions (20+)
        print("Seeding Transactions...")
        # Get active loans with schedules
        active_loans = db.query(Loan).filter(Loan.status == "Active").all()
        
        for _ in range(30):
            if not active_loans:
                break
            loan = random.choice(active_loans)
            # Find a pending schedule item
            schedule = db.query(RepaymentSchedule).filter(
                RepaymentSchedule.loan_id == loan.id,
                RepaymentSchedule.status == "Pending"
            ).order_by(RepaymentSchedule.due_date).first()
            
            if not schedule:
                continue
                
            txn_type = random.choice(["Cash", "Cheque", "Transfer"])
            txn = Transaction(
                loan_id=loan.id,
                repayment_schedule_id=schedule.id,
                transaction_type=txn_type,
                payment_mode=txn_type,
                amount_paid=schedule.expected_amount,
                transaction_date=datetime.now() - timedelta(days=random.randint(0, 30)),
                description=f"Automated seed payment for installment",
                status="Cleared",
                remarks="Seed data"
            )
            if txn_type == "Cheque":
                txn.cheque_number = f"{random.randint(100000, 999999)}"
                txn.bank_name = random.choice(["HDFC", "ICICI", "SBI", "AXIS"])
                txn.cheque_date = txn.transaction_date.date()
                txn.clearance_date = txn.transaction_date.date() + timedelta(days=2)
            
            db.add(txn)
            schedule.status = "Paid"
            
        db.flush()
        print(f"Transactions seeded. Total transactions: {db.query(Transaction).count()}")

        db.commit()
        print("Database seeding completed with 20+ records in all main tables.")
        
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_all()
