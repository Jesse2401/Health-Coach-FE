"""
Seed data for medical protocols.
Run this script to populate the database with initial protocols.
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal, engine, Base
from app.models.protocol import Protocol
from app.models import User, Message, Memory  # Import all models to register them


PROTOCOLS = [
    {
        "name": "Fever Management",
        "category": "medical",
        "keywords": ["fever", "temperature", "hot", "chills", "sweating", "flu", "sick", "warm", "burning"],
        "content": """When user mentions fever or high temperature:
1. Ask about the temperature reading if they have one
2. Ask about duration (how long they've had it)
3. Ask about other symptoms (headache, body aches, cough, etc.)
4. Recommend:
   - Rest and stay hydrated (water, clear broths, electrolyte drinks)
   - Over-the-counter fever reducers like acetaminophen or ibuprofen (if no contraindications)
   - Light clothing and cool compresses
   - Monitor temperature regularly
5. URGENT: Recommend seeking immediate medical care if:
   - Temperature above 103°F (39.4°C) in adults
   - Fever lasting more than 3 days
   - Severe headache, stiff neck, or confusion
   - Difficulty breathing
   - Any fever in infants under 3 months""",
        "priority": 10
    },
    {
        "name": "Stomach Ache / Digestive Issues",
        "category": "medical",
        "keywords": ["stomach", "ache", "pain", "nausea", "vomiting", "diarrhea", "bloating", "cramps", "indigestion", "belly", "abdomen", "tummy", "gastric", "digestive"],
        "content": """When user mentions stomach pain or digestive issues:
1. Ask about location of pain (upper, lower, left, right)
2. Ask about type of pain (sharp, dull, cramping, burning)
3. Ask about timing (after eating, constant, intermittent)
4. Ask about other symptoms (nausea, vomiting, diarrhea, constipation)
5. Recommend:
   - BRAT diet (bananas, rice, applesauce, toast) for upset stomach
   - Stay hydrated with small sips of water or clear fluids
   - Avoid spicy, fatty, or acidic foods
   - Ginger tea or peppermint tea may help with nausea
   - Rest and avoid strenuous activity
6. URGENT: Recommend immediate medical attention if:
   - Severe or sudden onset pain
   - Blood in vomit or stool
   - High fever with stomach pain
   - Pain that doesn't improve after 24-48 hours
   - Signs of dehydration (dizziness, dark urine, dry mouth)""",
        "priority": 10
    },
    {
        "name": "Headache Management",
        "category": "medical",
        "keywords": ["headache", "head", "migraine", "pain", "throbbing", "tension", "pressure", "temples"],
        "content": """When user mentions headache:
1. Ask about type (throbbing, pressure, sharp)
2. Ask about location (forehead, temples, back of head, one-sided)
3. Ask about triggers (stress, lack of sleep, dehydration, screen time)
4. Ask about frequency (occasional, frequent, daily)
5. Recommend:
   - Rest in a quiet, dark room
   - Stay hydrated
   - Apply cold or warm compress
   - Over-the-counter pain relievers (if appropriate)
   - Reduce screen time and take breaks
   - Practice relaxation techniques
6. URGENT: Seek immediate care if:
   - Sudden, severe "thunderclap" headache
   - Headache with fever, stiff neck, confusion
   - Headache after head injury
   - Vision changes or weakness
   - Worst headache of their life""",
        "priority": 9
    },
    {
        "name": "Sleep Issues",
        "category": "medical",
        "keywords": ["sleep", "insomnia", "tired", "fatigue", "exhausted", "cant sleep", "waking", "restless", "drowsy", "sleepy"],
        "content": """When user mentions sleep problems:
1. Ask about the specific issue (falling asleep, staying asleep, waking early)
2. Ask about sleep schedule and duration
3. Ask about lifestyle factors (caffeine, screen time, stress)
4. Ask about sleep environment (dark, quiet, comfortable)
5. Recommend:
   - Consistent sleep schedule (same time every day)
   - Avoid screens 1 hour before bed
   - Limit caffeine after noon
   - Create a relaxing bedtime routine
   - Keep bedroom cool, dark, and quiet
   - Exercise regularly but not close to bedtime
   - Consider relaxation techniques or meditation
6. Suggest consulting a doctor if:
   - Chronic insomnia (more than 3 weeks)
   - Excessive daytime sleepiness affecting daily life
   - Suspected sleep apnea (snoring, gasping)""",
        "priority": 7
    },
    {
        "name": "Stress and Anxiety",
        "category": "medical",
        "keywords": ["stress", "anxiety", "anxious", "worried", "panic", "nervous", "overwhelmed", "tense", "mental", "depressed", "sad"],
        "content": """When user mentions stress or anxiety:
1. Acknowledge their feelings with empathy
2. Ask about triggers or causes
3. Ask about physical symptoms (racing heart, tension, sleep issues)
4. Ask about duration and impact on daily life
5. Recommend:
   - Deep breathing exercises (4-7-8 technique)
   - Progressive muscle relaxation
   - Regular physical activity
   - Limiting caffeine and alcohol
   - Talking to supportive friends/family
   - Journaling or mindfulness practices
   - Taking breaks and setting boundaries
6. Strongly encourage professional help if:
   - Persistent anxiety affecting daily functioning
   - Panic attacks
   - Thoughts of self-harm (provide crisis resources)
   - Symptoms lasting more than 2 weeks
Note: Always be supportive and non-judgmental. Mental health is as important as physical health.""",
        "priority": 8
    },
    {
        "name": "Cold and Flu Symptoms",
        "category": "medical",
        "keywords": ["cold", "flu", "cough", "sneeze", "runny nose", "congestion", "sore throat", "stuffy", "mucus", "phlegm"],
        "content": """When user mentions cold or flu symptoms:
1. Ask about specific symptoms (cough, congestion, sore throat, body aches)
2. Ask about duration
3. Ask about fever presence
4. Recommend:
   - Rest and stay home to recover
   - Stay well hydrated (water, warm teas, broths)
   - Honey for cough (not for children under 1)
   - Salt water gargle for sore throat
   - Humidifier for congestion
   - Over-the-counter cold medications as appropriate
   - Vitamin C and zinc may help reduce duration
5. Seek medical care if:
   - High fever (above 103°F)
   - Symptoms lasting more than 10 days
   - Difficulty breathing or chest pain
   - Severe sore throat with difficulty swallowing
   - Symptoms that improve then worsen""",
        "priority": 8
    },
    {
        "name": "Refund and Billing Policy",
        "category": "policy",
        "keywords": ["refund", "money", "cancel", "subscription", "billing", "payment", "charge", "cost", "price", "pay"],
        "content": """When user asks about refunds or billing:
1. Express understanding of their concern
2. Explain that billing inquiries should be directed to customer support
3. Provide general information:
   - Subscription can be cancelled anytime
   - Refunds are handled on a case-by-case basis
   - Contact support@healthcoach.example.com for billing issues
4. Redirect conversation back to health coaching if appropriate
Note: As a health coach, focus on health-related support. Direct billing questions to appropriate channels.""",
        "priority": 5
    },
    {
        "name": "Emergency Situations",
        "category": "medical",
        "keywords": ["emergency", "911", "ambulance", "dying", "heart attack", "stroke", "cant breathe", "unconscious", "bleeding", "severe", "urgent"],
        "content": """CRITICAL: When user describes emergency symptoms:
1. IMMEDIATELY recommend calling emergency services (911 in US)
2. Emergency symptoms include:
   - Chest pain or pressure
   - Difficulty breathing
   - Signs of stroke (face drooping, arm weakness, speech difficulty)
   - Severe bleeding
   - Loss of consciousness
   - Severe allergic reaction
   - Thoughts of suicide or self-harm
3. Stay calm and supportive
4. Do NOT attempt to diagnose or provide treatment for emergencies
5. Encourage them to stay on the line with emergency services
6. For mental health crisis: National Suicide Prevention Lifeline 988""",
        "priority": 100
    }
]


async def seed_protocols():
    """Seed the database with initial protocols."""
    # Create tables first
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/verified.")
    
    async with AsyncSessionLocal() as session:
        # Check if protocols already exist
        result = await session.execute(select(Protocol).limit(1))
        if result.scalar_one_or_none():
            print("Protocols already seeded. Skipping.")
            return
        
        # Insert protocols
        for protocol_data in PROTOCOLS:
            protocol = Protocol(**protocol_data)
            session.add(protocol)
        
        await session.commit()
        print(f"Successfully seeded {len(PROTOCOLS)} protocols.")


if __name__ == "__main__":
    asyncio.run(seed_protocols())

