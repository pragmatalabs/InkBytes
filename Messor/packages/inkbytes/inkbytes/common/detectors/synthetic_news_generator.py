import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_synthetic_news_data(n_articles=1000, n_events=10, max_days=30):
    """
    Generate synthetic news data for testing.

    Parameters:
    -----------
    n_articles : int
        Number of articles to generate
    n_events : int
        Number of detectors to distribute articles across
    max_days : int
        Maximum number of days for event duration

    Returns:
    --------
    pandas.DataFrame
        Dataframe containing synthetic news data
    """
    # Create event templates
    event_templates = [
        {"name": "Election", "keywords": ["election", "vote", "campaign", "ballot", "candidate", "politics", "president", "voter"]},
        {"name": "Natural Disaster", "keywords": ["hurricane", "earthquake", "flood", "tornado", "disaster", "relief", "emergency", "victim"]},
        {"name": "Technology Launch", "keywords": ["launch", "technology", "product", "innovation", "company", "release", "announce", "feature"]},
        {"name": "Sports Event", "keywords": ["game", "match", "tournament", "player", "team", "championship", "victory", "compete"]},
        {"name": "Financial News", "keywords": ["stock", "market", "investment", "economy", "financial", "bank", "trade", "investor"]},
        {"name": "International Conflict", "keywords": ["war", "conflict", "military", "troops", "attack", "defense", "peace", "negotiate"]},
        {"name": "Health Crisis", "keywords": ["health", "disease", "vaccine", "treatment", "hospital", "patient", "doctor", "outbreak"]},
        {"name": "Entertainment", "keywords": ["movie", "music", "celebrity", "award", "release", "performance", "actor", "director"]},
        {"name": "Science Discovery", "keywords": ["research", "discovery", "scientist", "study", "experiment", "breakthrough", "innovation", "laboratory"]},
        {"name": "Environmental Issue", "keywords": ["climate", "environment", "pollution", "sustainable", "conservation", "carbon", "green", "recycle"]}
    ]

    # Add more templates if needed
    while len(event_templates) < n_events:
        event_templates.append(event_templates[len(event_templates) % 10])

    # Select event templates for this run
    selected_events = event_templates[:n_events]

    # Generate start dates for detectors
    end_date = datetime.now()
    start_date = end_date - timedelta(days=max_days)

    event_data = []
    for i, event in enumerate(selected_events):
        # Decide number of articles for this event
        articles_per_event = max(3, int(np.random.normal(n_articles / n_events, n_articles / (n_events * 3))))

        # Generate event date range
        event_start = start_date + timedelta(days=np.random.randint(0, max_days // 2))
        event_duration = np.random.randint(1, max_days // 2)

        # Generate articles for the event
        for j in range(articles_per_event):
            # Decide article date
            days_from_start = min(np.random.randint(0, event_duration + 1), event_duration)
            article_date = event_start + timedelta(days=days_from_start)

            # Generate article text
            keywords = event["keywords"]
            text_length = np.random.randint(50, 500)

            # Create article with event keywords
            text_words = []
            for _ in range(text_length):
                # 30% chance of using an event-specific keyword
                if np.random.random() < 0.3:
                    text_words.append(np.random.choice(keywords))
                else:
                    # Generate a random word
                    text_words.append(f"word{np.random.randint(1, 1000)}")

            # Add some common words
            common_words = ["the", "and", "of", "in", "to", "a", "is", "that", "for", "with"]
            for i in range(len(text_words)):
                if np.random.random() < 0.2:
                    text_words.insert(i, np.random.choice(common_words))

            # Create article title
            title_words = []
            for _ in range(np.random.randint(5, 12)):
                if np.random.random() < 0.5:
                    title_words.append(np.random.choice(keywords))
                else:
                    title_words.append(f"word{np.random.randint(1, 1000)}")

            text = " ".join(text_words)
            title = " ".join(title_words).capitalize()

            # Add to event data
            event_data.append({
                "date": article_date,
                "title": title,
                "text": text,
                "true_event_id": i,  # True event ID for evaluation
                "event_name": event["name"]
            })

    # Convert to DataFrame
    df = pd.DataFrame(event_data)

    # Add some noise articles
    n_noise = int(n_articles * 0.2)  # 20% noise articles
    noise_articles = []

    for _ in range(n_noise):
        # Generate random date
        days_from_start = np.random.randint(0, max_days)
        article_date = start_date + timedelta(days=days_from_start)

        # Generate random text
        text_length = np.random.randint(50, 500)
        text_words = [f"noise{np.random.randint(1, 1000)}" for _ in range(text_length)]

        # Add some common words
        common_words = ["the", "and", "of", "in", "to", "a", "is", "that", "for", "with"]
        for i in range(len(text_words)):
            if np.random.random() < 0.2:
                text_words.insert(i, np.random.choice(common_words))

        # Create title
        title_words = [f"noise{np.random.randint(1, 1000)}" for _ in range(np.random.randint(5, 12))]

        text = " ".join(text_words)
        title = " ".join(title_words).capitalize()

        # Add to noise data
        noise_articles.append({
            "date": article_date,
            "title": title,
            "text": text,
            "true_event_id": -1,  # -1 indicates noise
            "event_name": "Noise"
        })

    # Add noise to dataframe
    df = pd.concat([df, pd.DataFrame(noise_articles)], ignore_index=True)

    # Shuffle the dataframe
    df = df.sample(frac=1).reset_index(drop=True)

    print(f"Generated {len(df)} articles across {n_events} detectors (plus noise)")
    return df
if __name__ == "__main__":
    data=generate_synthetic_news_data(n_articles=1000, n_events=10, max_days=30)
    #save data to csv
    data.to_csv("synthetic_news_data.csv", index=False)