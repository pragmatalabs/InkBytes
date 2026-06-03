#!/usr/bin/env python3
"""
Generate a news event detection model using synthetic data.

This script generates synthetic news data and trains a NewsEventDetector model
that can be saved and later used for detecting events in real news data.
"""

import argparse
import os
import matplotlib.pyplot as plt
import pandas as pd
import nltk

# Import the NewsEventDetector class and helper functions
from event_detector import NewsEventDetector, plot_event_timeline, evaluate_clustering
from synthetic_news_generator import generate_synthetic_news_data

# Download required NLTK resources
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except:
    print("Warning: Could not download NLTK resources. If you haven't installed them before, some functionality may be limited.")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate a news event detection model using synthetic data")

    parser.add_argument("--n_articles", type=int, default=500,
                        help="Number of synthetic articles to generate")
    parser.add_argument("--n_events", type=int, default=5,
                        help="Number of synthetic events to generate")
    parser.add_argument("--max_days", type=int, default=14,
                        help="Maximum duration in days for synthetic events")
    parser.add_argument("--embedding_size", type=int, default=40,
                        help="Size of document embeddings")
    parser.add_argument("--min_cluster_size", type=int, default=3,
                        help="Minimum number of articles to form a cluster")
    parser.add_argument("--eps", type=float, default=0.3,
                        help="Maximum distance between articles in the same neighborhood for DBSCAN")
    parser.add_argument("--vectorizer", type=str, default="tfidf_lsa",
                        choices=["tfidf_lsa", "doc2vec", "spacy"],
                        help="Vectorization method to use")
    parser.add_argument("--output_dir", type=str, default="output",
                        help="Directory to save output files")
    parser.add_argument("--model_name", type=str, default="news_event_detector.pkl",
                        help="Filename for the saved model")

    return parser.parse_args()

def main():
    """Main function to generate the model."""
    # Parse command line arguments
    args = parse_args()

    print("\n===== News Event Detection Model Generator =====\n")

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate synthetic data
    print(f"\nGenerating synthetic news data ({args.n_articles} articles, {args.n_events} events)...")
    df = generate_synthetic_news_data(
        n_articles=args.n_articles,
        n_events=args.n_events,
        max_days=args.max_days
    )

    # Save the synthetic data
    synth_data_path = os.path.join(args.output_dir, "synthetic_news_data.csv")
    df.to_csv(synth_data_path, index=False)
    print(f"Synthetic data saved to {synth_data_path}")

    # Create event detector
    detector = NewsEventDetector(
        embedding_size=args.embedding_size,
        min_cluster_size=args.min_cluster_size,
        eps=args.eps
    )

    # Detect events using the specified vectorizer
    print(f"\nDetecting events using {args.vectorizer}...")
    df_clustered, events = detector.detect_events(
        df,
        vectorizer_method=args.vectorizer
    )

    # Evaluate clustering
    metrics = evaluate_clustering(df_clustered)

    # Save evaluation metrics
    metrics_path = os.path.join(args.output_dir, "evaluation_metrics.txt")
    with open(metrics_path, 'w') as f:
        f.write("Clustering Evaluation Metrics:\n")
        for metric, value in metrics.items():
            f.write(f"{metric}: {value:.4f}\n")
    print(f"Evaluation metrics saved to {metrics_path}")

    # Create event timeline
    timeline_df = detector.create_event_timeline(df_clustered, events)

    # Save timeline data
    if timeline_df is not None and not timeline_df.empty:
        timeline_path = os.path.join(args.output_dir, "event_timeline.csv")
        timeline_df.to_csv(timeline_path, index=False)
        print(f"Event timeline saved to {timeline_path}")

        # Plot and save event timeline
        timeline_plot_path = os.path.join(args.output_dir, "event_timeline.png")
        plot_event_timeline(timeline_df, save_path=timeline_plot_path)

    # Get evolving events
    evolving_events = detector.get_evolving_events(df_clustered, events, min_duration=2)

    # Print event information
    print("\nDetected Events:")
    for event_id, event_info in events.items():
        print(f"\nEvent {event_id}:")
        print(f"  Headline: {event_info['headline']}")
        print(f"  Articles: {event_info['article_count']}")
        if event_info['start_date'] is not None:
            print(f"  Duration: {event_info['duration_days']} days ({event_info['start_date'].date()} to {event_info['end_date'].date()})")

    # Train Doc2Vec model if requested
    if args.vectorizer == "doc2vec":
        print("\nTraining Doc2Vec model...")
        detector.set_vectorizer_method('doc2vec')
        detector.create_doc2vec_model(df_clustered['processed_text'].tolist(), vector_size=args.embedding_size, epochs=20)

    # Save model
    model_path = os.path.join(args.output_dir, args.model_name)
    detector.save_model(model_path)
    print(f"\nModel saved to {model_path}")

    # Example of finding related articles
    print("\nExample: Finding related articles")
    central_article_idx = events[0]['central_article_idx'] if 0 in events else 0
    article_text = df.iloc[central_article_idx]['text']

    related_articles = detector.find_related_articles(article_text, df, n=3)
    print(f"Articles related to: {df.iloc[central_article_idx]['title']}")
    for _, article in related_articles.iterrows():
        print(f"  - {article['title']} (Similarity: {article['similarity']:.4f})")

    print("\n===== Model Generation Complete =====")
    print(f"All output files saved to the '{args.output_dir}' directory")
    print(f"To use this model for detecting events in real news data, load it with:")
    print(f"  detector = NewsEventDetector.load_model('{model_path}')")

if __name__ == "__main__":
    main()