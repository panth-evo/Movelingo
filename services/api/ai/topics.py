import random

TOPICS = [
    "housing and finding an apartment",
    "work, job interviews, and workplace culture",
    "bureaucracy, visas, and registration",
    "health, doctors, and medical insurance",
    "school, university, and education",
    "banking, taxes, and finances",
    "transport, commuting, and getting around",
    "daily life, shopping, and social integration"
]

def get_random_topic(seed=None) -> str:
    if seed:
        random.seed(seed)
    return random.choice(TOPICS)
