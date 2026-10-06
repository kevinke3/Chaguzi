"""Seed demo data for Chaguzi."""
import os
from datetime import datetime, timedelta


def seed_demo_data(app):
    from extensions import db
    from models.organization import Organization
    from models.user import User
    from models.election import Election
    from models.position import Position
    from models.candidate import Candidate
    from models.vote import Vote
    
    with app.app_context():
        if Organization.query.count() > 0:
            print('Demo data already exists. Skipping.')
            return
        
        # Organization 1
        org = Organization(
            name='Sunrise University',
            slug='sunrise-university',
            org_type='university',
            email='admin@sunrise.edu',
            phone='+254 700 000 001',
            location='Nairobi, Kenya',
            description='Sunrise University Student Council Elections',
            voter_id_required=True,
            voter_id_label='Student ID',
        )
        db.session.add(org)
        db.session.flush()
        
        # Admin
        admin = User(
            organization_id=org.id,
            role='admin',
            full_name='Sarah Admin',
            email='admin@sunrise.edu',
            phone='+254 700 000 001',
            is_active=True, is_approved=True,
        )
        admin.set_password('Admin@123')
        db.session.add(admin)
        
        # Organization 2
        org2 = Organization(
            name='Grace Community Church',
            slug='grace-community-church',
            org_type='church',
            email='admin@gracechurch.org',
            phone='+254 700 000 002',
            location='Kampala, Uganda',
            voter_id_required=False,
            voter_id_label='Membership Number',
        )
        db.session.add(org2)
        db.session.flush()
        
        admin2 = User(
            organization_id=org2.id,
            role='admin',
            full_name='Pastor John',
            email='admin@gracechurch.org',
            is_active=True, is_approved=True,
        )
        admin2.set_password('Admin@123')
        db.session.add(admin2)
        db.session.flush()
        
        # Voters
        voters = []
        for i in range(1, 6):
            v = User(
                organization_id=org.id,
                role='voter',
                full_name=f'Student {i}',
                email=f'student{i}@sunrise.edu',
                voter_id=f'SU-{1000 + i}',
                is_active=True, is_approved=True,
            )
            v.set_password('Voter@123')
            db.session.add(v)
            voters.append(v)
        
        db.session.flush()
        
        # Election
        now = datetime.utcnow()
        election = Election(
            organization_id=org.id,
            name='2025 Student Council Election',
            description='Annual student leadership election.',
            election_type='student_council',
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(days=2),
            result_visibility='live',
            status='active',
            created_by=admin.id,
        )
        db.session.add(election)
        db.session.flush()
        
        # Positions and candidates
        chair = Position(election_id=election.id, title='Chairperson', order_index=0)
        db.session.add(chair)
        sec = Position(election_id=election.id, title='Secretary', order_index=1)
        db.session.add(sec)
        db.session.flush()
        
        candidates = [
            (chair, 'Amina Yusuf', 'Progress and Inclusion'),
            (chair, 'Brian Otieno', 'Unity and Growth'),
            (chair, 'Cynthia Wanjiru', 'Innovation First'),
            (sec, 'David Kimani', 'Efficient Records'),
            (sec, 'Esther Akinyi', 'Transparent Communication'),
        ]
        for pos, name, desc in candidates:
            c = Candidate(
                position_id=pos.id, organization_id=org.id,
                name=name, description=desc,
                manifesto=f'My manifesto: {desc}',
            )
            db.session.add(c)
        
        db.session.commit()
        print('Demo data seeded successfully!')
        print('Admin login: admin@sunrise.edu / Admin@123')
        print('Voter login: student1@sunrise.edu / Voter@123')