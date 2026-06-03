import logging
import pickle
import re

import numpy as np
import pandas as pd
import sklearn.decomposition
import spacy
from gensim.models import Doc2Vec
from gensim.models.doc2vec import TaggedDocument
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer

# Set up logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

class NewsEventDetector:
    """
    A class for detecting and tracking news detectors across articles.
    """

    def __init__(self, embedding_size=300, min_cluster_size=2, eps=0.3):
        """
        Initialize the event detector.

        Parameters:
        -----------
        embedding_size : int
            Size of document embeddings
        min_cluster_size : int
            Minimum number of articles to form a cluster (event)
        eps : float
            Maximum distance between articles in the same neighborhood for DBSCAN
        """
        self.embedding_size = embedding_size
        self.min_cluster_size = min_cluster_size
        self.eps = eps
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.nlp = None  # Will be initialized when needed
        self.tfidf_vectorizer = None
        self.lsa_model = None
        self.doc2vec_model = None
        self.dbscan = None
        self.vectorizer_method = 'tfidf_lsa'  # Default vectorizer method

    def preprocess_text(self, text):
        """
        Preprocess the text by lowercasing, removing punctuation,
        removing stopwords, and lemmatizing.

        Parameters:
        -----------
        text : str
            Input text to preprocess

        Returns:
        --------
        str
            Preprocessed text
        """
        if not isinstance(text, str):
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+|www\S+', '', text)

        # Remove punctuation and numbers
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)

        # Tokenize
        tokens = word_tokenize(text)

        # Remove stopwords and lemmatize
        tokens = [self.lemmatizer.lemmatize(token) for token in tokens if token not in self.stop_words and len(token) > 2]

        # Join back into a string
        return ' '.join(tokens)

    def extract_entities(self, text):
        """
        Extract named entities from text.

        Parameters:
        -----------
        text : str
            Input text

        Returns:
        --------
        list
            List of extracted named entities
        """
        if not isinstance(text, str):
            return []

        # Initialize spaCy if not already done
        if self.nlp is None:
            try:
                self.nlp = spacy.load('en_core_web_sm')
            except:
                # If model not found, download it
                import subprocess
                subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'])
                self.nlp = spacy.load('en_core_web_sm')

        doc = self.nlp(text)
        entities = []

        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'FAC']:
                entities.append(ent.text.lower())

        return entities

    def create_tfidf_lsa_vectorizer(self, texts, n_components=None):
        """
        Create a TF-IDF + LSA vectorizer pipeline.

        Parameters:
        -----------
        texts : list
            List of text documents
        n_components : int
            Number of components for LSA
        """
        if n_components is None:
            n_components = min(40, len(texts) - 1)
        # Create and fit TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            min_df=2,
            max_df=0.85,
            sublinear_tf=True
        )

        # Fit the vectorizer first to get the feature count
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
        n_features = tfidf_matrix.shape[1]

        # Adjust n_components to be at most the number of features
        n_components = min(n_components, n_features - 1)

        # Create LSA model with adjusted n_components
        self.lsa_model = Pipeline([
            ('svd', sklearn.decomposition.TruncatedSVD(n_components=n_components)),
            ('normalizer', Normalizer(copy=False))
        ])

        # Fit the pipeline
        self.lsa_model.fit(tfidf_matrix)

        print(f"Created TF-IDF + LSA vectorizer with {n_components} components")

    def create_doc2vec_model(self, texts, tagged_docs=None, vector_size=300, epochs=40):
        """
        Create and train a Doc2Vec model.

        Parameters:
        -----------
        texts : list
            List of text documents
        tagged_docs : list, optional
            List of TaggedDocument objects
        vector_size : int
            Size of document vectors
        epochs : int
            Number of training epochs
        """
        if tagged_docs is None:
            # Create tagged documents
            tagged_docs = [TaggedDocument(words=doc.split(), tags=[str(i)])
                           for i, doc in enumerate(texts)]

        # Create and train the Doc2Vec model
        self.doc2vec_model = Doc2Vec(
            vector_size=vector_size,
            min_count=2,
            epochs=epochs,
            workers=4,
            dm=1  # Use PV-DM model
        )

        # Build vocabulary
        self.doc2vec_model.build_vocab(tagged_docs)

        # Train the model
        print(f"Training Doc2Vec model with vector size {vector_size}...")
        self.doc2vec_model.train(
            tagged_docs,
            total_examples=self.doc2vec_model.corpus_count,
            epochs=self.doc2vec_model.epochs
        )

        print(f"Trained Doc2Vec model (vector size: {vector_size}, epochs: {epochs})")

    def set_vectorizer_method(self, method):
        """
        Set the vectorization method.

        Parameters:
        -----------
        method : str
            Vectorization method ('tfidf_lsa', 'doc2vec', or 'spacy')
        """
        valid_methods = ['tfidf_lsa', 'doc2vec', 'spacy']

        if method not in valid_methods:
            raise ValueError(f"Invalid vectorizer method: {method}. Choose from {valid_methods}")

        self.vectorizer_method = method
        print(f"Set vectorizer method to '{method}'")

    def vectorize_documents(self, texts):
        """
        Convert texts to document vectors using the selected method.

        Parameters:
        -----------
        texts : list
            List of text documents

        Returns:
        --------
        numpy.ndarray
            Document vectors
        """
        if self.vectorizer_method == 'tfidf_lsa':
            # Check if models are initialized
            if self.tfidf_vectorizer is None or self.lsa_model is None:
                self.create_tfidf_lsa_vectorizer(texts)

            # Transform texts
            tfidf_matrix = self.tfidf_vectorizer.transform(texts)
            return self.lsa_model.transform(tfidf_matrix)

        elif self.vectorizer_method == 'doc2vec':
            # Check if model is initialized
            if self.doc2vec_model is None:
                self.create_doc2vec_model(texts)

            # Infer vectors
            vectors = np.zeros((len(texts), self.doc2vec_model.vector_size))

            for i, text in enumerate(texts):
                tokens = text.split()
                vectors[i] = self.doc2vec_model.infer_vector(tokens)

            return vectors

        elif self.vectorizer_method == 'spacy':
            # Initialize spaCy if not already done
            if self.nlp is None:
                try:
                    self.nlp = spacy.load('en_core_web_md')  # Use medium model with word vectors
                except:
                    # If model not found, download it
                    import subprocess
                    subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_md'])
                    self.nlp = spacy.load('en_core_web_md')

            # Vectorize texts
            vectors = np.zeros((len(texts), 300))  # spaCy's word vectors are 300-dimensional

            for i, text in enumerate(texts):
                doc = self.nlp(text)
                if doc.has_vector:
                    vectors[i] = doc.vector

            return vectors

    def cluster_articles(self, vectors, eps=None, min_samples=None):
        """
        Cluster article vectors using DBSCAN.

        Parameters:
        -----------
        vectors : numpy.ndarray
            Document vectors
        eps : float, optional
            DBSCAN eps parameter
        min_samples : int, optional
            DBSCAN min_samples parameter

        Returns:
        --------
        numpy.ndarray
            Cluster labels for each article
        """
        # Set parameters
        if eps is None:
            eps = self.eps
        if min_samples is None:
            min_samples = self.min_cluster_size

        # Create and fit DBSCAN clustering
        self.dbscan = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric='cosine'
        )

        labels = self.dbscan.fit_predict(vectors)

        # Count clusters (excluding noise points with label -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        print(f"DBSCAN clustering found {n_clusters} clusters and {n_noise} noise points")

        return labels

    def get_cluster_centers(self, vectors, labels):
        """
        Compute the center vector for each cluster.

        Parameters:
        -----------
        vectors : numpy.ndarray
            Document vectors
        labels : numpy.ndarray
            Cluster labels for each article

        Returns:
        --------
        dict
            Dictionary mapping cluster labels to center vectors
        """
        cluster_centers = {}

        # Get unique cluster labels (excluding noise)
        unique_labels = set(labels)
        if -1 in unique_labels:
            unique_labels.remove(-1)

        # Compute center for each cluster
        for label in unique_labels:
            cluster_vectors = vectors[labels == label]
            center = np.mean(cluster_vectors, axis=0)
            cluster_centers[label] = center

        return cluster_centers

    def get_central_articles(self, vectors, labels, texts, n=1):
        """
        Find the central article(s) for each cluster.

        Parameters:
        -----------
        vectors : numpy.ndarray
            Document vectors
        labels : numpy.ndarray
            Cluster labels for each article
        texts : list
            List of text documents
        n : int
            Number of central articles to return per cluster

        Returns:
        --------
        dict
            Dictionary mapping cluster labels to central article indices
        """
        cluster_centers = self.get_cluster_centers(vectors, labels)
        central_articles = {}

        # Get unique cluster labels (excluding noise)
        unique_labels = set(labels)
        if -1 in unique_labels:
            unique_labels.remove(-1)

        # Find central articles for each cluster
        for label in unique_labels:
            cluster_indices = np.where(labels == label)[0]
            cluster_vectors = vectors[cluster_indices]

            # Compute similarities to cluster center
            center = cluster_centers[label]
            similarities = cosine_similarity(cluster_vectors, center.reshape(1, -1)).flatten()

            # Get indices of most similar articles
            central_indices = cluster_indices[np.argsort(similarities)[-n:]]
            central_articles[label] = central_indices.tolist()

        return central_articles

    def detect_events(self, df, text_column='text', title_column='title', date_column='date',
                      vectorizer_method='tfidf_lsa', eps=None, min_samples=None):
        """
        Detect detectors from a dataframe of news articles.

        Parameters:
        -----------
        df : pandas.DataFrame
            Dataframe containing news articles
        text_column : str
            Column containing article text
        title_column : str
            Column containing article titles
        date_column : str
            Column containing article dates
        vectorizer_method : str
            Vectorization method ('tfidf_lsa', 'doc2vec', or 'spacy')
        eps : float, optional
            DBSCAN eps parameter
        min_samples : int, optional
            DBSCAN min_samples parameter

        Returns:
        --------
        pandas.DataFrame
            Dataframe with added 'event_id' column
        dict
            Dictionary containing event information
        """
        # Set vectorizer method
        self.set_vectorizer_method(vectorizer_method)

        # Preprocess texts
        print("Preprocessing texts...")
        df['processed_text'] = df[text_column].apply(self.preprocess_text)

        # Extract entities if using spaCy
        if vectorizer_method == 'spacy':
            print("Extracting named entities...")
            df['entities'] = df[text_column].apply(self.extract_entities)

        # Vectorize documents
        print("Vectorizing documents...")
        vectors = self.vectorize_documents(df['processed_text'].tolist())

        # Cluster articles
        print("Clustering articles...")
        labels = self.cluster_articles(vectors, eps, min_samples)

        # Add cluster labels to dataframe
        df['event_id'] = labels

        # Get central articles for each cluster
        central_articles = self.get_central_articles(vectors, labels, df['processed_text'].tolist())

        # Prepare event information
        events = {}

        # Get unique cluster labels (excluding noise)
        unique_labels = set(labels)
        if -1 in unique_labels:
            unique_labels.remove(-1)

        # Extract event information
        for label in unique_labels:
            event_articles = df[df['event_id'] == label]
            central_idx = central_articles[label][0]  # Get first central article

            # Get headline from central article
            headline = df.iloc[central_idx][title_column] if title_column in df.columns else ""

            # Get date range
            if date_column in df.columns:
                try:
                    # Convert dates safely with error handling
                    dates = pd.to_datetime(event_articles[date_column], errors='coerce')
                    
                    # Remove NaT values before calculating min/max
                    valid_dates = dates.dropna()
                    
                    if not valid_dates.empty:
                        start_date = valid_dates.min()
                        end_date = valid_dates.max()
                        duration = (end_date - start_date).days + 1
                    else:
                        start_date = None
                        end_date = None
                        duration = None
                except Exception as e:
                    print(f"Error processing dates for event {label}: {e}")
                    start_date = None
                    end_date = None
                    duration = None
            else:
                start_date = None
                end_date = None
                duration = None

            # Store event information
            events[label] = {
                'headline': headline,
                'central_article_idx': central_idx,
                'article_count': len(event_articles),
                'start_date': start_date,
                'end_date': end_date,
                'duration_days': duration,
                'article_indices': event_articles.index.tolist()
            }

        print(f"Detected {len(events)} detectors")
        return df, events

    def create_event_timeline(self, df, events, date_column='date', title_column='title'):
        """
        Create a timeline of detectors.

        Parameters:
        -----------
        df : pandas.DataFrame
            Dataframe containing news articles with 'event_id' column
        detectors : dict
            Dictionary containing event information
        date_column : str
            Column containing article dates
        title_column : str
            Column containing article titles

        Returns:
        --------
        pandas.DataFrame
            Dataframe containing event timeline
        """
        if date_column not in df.columns:
            print(f"Date column '{date_column}' not found in dataframe")
            return None

        # Create timeline
        timeline = []

        for event_id, event_info in events.items():
            # Get articles for this event
            event_articles = df[df['event_id'] == event_id]

            # Sort by date
            event_articles = event_articles.sort_values(date_column)

            # Get headline
            headline = event_info['headline']

            # Add entries for each day in the event
            # First handle any missing dates
            event_articles[date_column] = pd.to_datetime(event_articles[date_column], errors='coerce')
            
            # Only group by valid dates
            valid_date_articles = event_articles.dropna(subset=[date_column])
            
            if not valid_date_articles.empty:
                for date, articles in valid_date_articles.groupby(date_column):
                    # Get representative article for this day
                    if len(articles) > 0:
                        article_idx = articles.index[0]
                        article_title = articles.iloc[0][title_column] if title_column in articles.columns else ""
    
                        timeline.append({
                            'date': date,
                            'event_id': event_id,
                            'headline': headline,
                            'article_count': len(articles),
                            'article_idx': article_idx,
                            'article_title': article_title
                        })
            else:
                # If no valid dates, still add an entry without a date
                article_idx = event_articles.index[0] if not event_articles.empty else None
                article_title = event_articles.iloc[0][title_column] if not event_articles.empty and title_column in event_articles.columns else ""
                
                timeline.append({
                    'date': None,  # No valid date
                    'event_id': event_id,
                    'headline': headline,
                    'article_count': len(event_articles),
                    'article_idx': article_idx,
                    'article_title': article_title
                })

        # Convert to dataframe and sort by date
        timeline_df = pd.DataFrame(timeline)
        if not timeline_df.empty:
            # Check if we have any valid dates to sort by
            if timeline_df['date'].notna().any():
                # Sort only by valid dates, keeping None values at the end
                timeline_df = timeline_df.sort_values('date', na_position='last')

        return timeline_df

    def find_related_articles(self, article_text, df, text_column='text', n=5):
        """
        Find articles related to a given article.

        Parameters:
        -----------
        article_text : str
            Text of the article to find related articles for
        df : pandas.DataFrame
            Dataframe containing news articles
        text_column : str
            Column containing article text
        n : int
            Number of related articles to return

        Returns:
        --------
        pandas.DataFrame
            Dataframe containing related articles
        """
        # Preprocess the input article text
        processed_text = self.preprocess_text(article_text)

        # Check if dataframe has processed text
        if 'processed_text' not in df.columns:
            df['processed_text'] = df[text_column].apply(self.preprocess_text)

        # Vectorize the input article
        if self.vectorizer_method == 'tfidf_lsa':
            # Transform text
            article_tfidf = self.tfidf_vectorizer.transform([processed_text])
            article_vector = self.lsa_model.transform(article_tfidf)

            # Get all article vectors
            all_tfidf = self.tfidf_vectorizer.transform(df['processed_text'].tolist())
            all_vectors = self.lsa_model.transform(all_tfidf)

        elif self.vectorizer_method == 'doc2vec':
            # Infer vector
            tokens = processed_text.split()
            article_vector = self.doc2vec_model.infer_vector(tokens).reshape(1, -1)

            # Get all article vectors
            all_vectors = np.zeros((len(df), self.doc2vec_model.vector_size))
            for i, text in enumerate(df['processed_text']):
                tokens = text.split()
                all_vectors[i] = self.doc2vec_model.infer_vector(tokens)

        elif self.vectorizer_method == 'spacy':
            # Get vector
            doc = self.nlp(processed_text)
            article_vector = doc.vector.reshape(1, -1)

            # Get all article vectors
            all_vectors = np.zeros((len(df), 300))
            for i, text in enumerate(df['processed_text']):
                doc = self.nlp(text)
                if doc.has_vector:
                    all_vectors[i] = doc.vector

        # Compute similarities
        similarities = cosine_similarity(article_vector, all_vectors).flatten()

        # Get indices of most similar articles
        similar_indices = np.argsort(similarities)[::-1][:n+1]  # +1 to account for self-similarity

        # Remove the article itself if it's in the dataframe
        similar_indices = [idx for idx in similar_indices if similarities[idx] < 0.999][:n]

        # Add similarity scores
        similar_df = df.iloc[similar_indices].copy()
        similar_df['similarity'] = similarities[similar_indices]

        return similar_df.sort_values('similarity', ascending=False)

    def get_evolving_events(self, df, events, date_column='date', min_duration=3):
        """
        Get events that evolve over time (spanning multiple days).

        Parameters:
        -----------
        df : pandas.DataFrame
            Dataframe containing news articles with 'event_id' column
        events : dict
            Dictionary containing event information
        date_column : str
            Column containing article dates
        min_duration : int
            Minimum duration in days for an event to be considered evolving

        Returns:
        --------
        dict
            Dictionary containing evolving event information
        """
        evolving_events = {}

        for event_id, event_info in events.items():
            # Check if the duration is valid and exceeds the minimum
            if (event_info['duration_days'] is not None and 
                event_info['start_date'] is not None and 
                event_info['end_date'] is not None and 
                event_info['duration_days'] >= min_duration):
                
                evolving_events[event_id] = event_info

        print(f"Found {len(evolving_events)} evolving events (spanning {min_duration}+ days)")
        return evolving_events

    def save_model(self, filepath):
        """
        Save the trained model to a file.

        Parameters:
        -----------
        filepath : str
            Path to save the model to
        """
        # Save vectorizer and clustering models
        model_data = {
            'vectorizer_method': self.vectorizer_method,
            'tfidf_vectorizer': self.tfidf_vectorizer,
            'lsa_model': self.lsa_model,
            'doc2vec_model': self.doc2vec_model,
            'dbscan': self.dbscan,
            'eps': self.eps,
            'min_cluster_size': self.min_cluster_size,
            'embedding_size': self.embedding_size
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        print(f"Model saved to {filepath}")

    @classmethod
    def load_model(cls, filepath):
        """
        Load a trained model from a file.

        Parameters:
        -----------
        filepath : str
            Path to load the model from

        Returns:
        --------
        NewsEventDetector
            Loaded model
        """
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        # Create new instance
        model = cls(
            embedding_size=model_data['embedding_size'],
            min_cluster_size=model_data['min_cluster_size'],
            eps=model_data['eps']
        )

        # Load model components
        model.vectorizer_method = model_data['vectorizer_method']
        model.tfidf_vectorizer = model_data['tfidf_vectorizer']
        model.lsa_model = model_data['lsa_model']
        model.doc2vec_model = model_data['doc2vec_model']
        model.dbscan = model_data['dbscan']

        print(f"Model loaded from {filepath}")
        return model

# Helper function to plot event timeline
def plot_event_timeline(timeline_df, figsize=(12, 8), save_path=None):
    """
    Plot a timeline of detectors.

    Parameters:
    -----------
    timeline_df : pandas.DataFrame
        Dataframe containing event timeline
    figsize : tuple
        Figure size
    save_path : str, optional
        Path to save the plot
    """
    import matplotlib.pyplot as plt

    if timeline_df is None or timeline_df.empty:
        print("Timeline is empty, nothing to plot")
        return

    plt.figure(figsize=figsize)

    # Get event information
    events = timeline_df['event_id'].unique()

    # Create y-positions for detectors
    event_positions = {event: i for i, event in enumerate(events)}

    # Plot detectors
    for event in events:
        event_data = timeline_df[timeline_df['event_id'] == event]

        # Get headline for this event
        headline = event_data['headline'].iloc[0]

        # Plot points for each day
        plt.plot(event_data['date'], [event_positions[event]] * len(event_data),
                 marker='o', linestyle='-', markersize=8, label=f"Event {event}: {headline}")

        # Add article count text
        for _, row in event_data.iterrows():
            plt.text(row['date'], event_positions[event] + 0.1, str(row['article_count']),
                     fontsize=8, ha='center')

    # Set labels and title
    plt.yticks(list(event_positions.values()), [f"Event {event}" for event in events])
    plt.xlabel('Date')
    plt.title('News Event Timeline')
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Format x-axis dates
    plt.gcf().autofmt_xdate()

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
        print(f"Timeline plot saved to {save_path}")
    else:
        plt.show()

    plt.close()

# Helper function to evaluate clustering results
def evaluate_clustering(df, event_column='event_id', true_event_column='true_event_id'):
    """
    Evaluate clustering results against ground truth.

    Parameters:
    -----------
    df : pandas.DataFrame
        Dataframe containing news articles
    event_column : str
        Column containing detected event IDs
    true_event_column : str
        Column containing true event IDs

    Returns:
    --------
    dict
        Dictionary containing evaluation metrics
    """
    from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score

    # Get event labels
    true_labels = df[true_event_column].values
    pred_labels = df[event_column].values

    # Calculate metrics
    ari = adjusted_rand_score(true_labels, pred_labels)
    ami = adjusted_mutual_info_score(true_labels, pred_labels)

    # Calculate purity
    contingency_matrix = pd.crosstab(df[true_event_column], df[event_column])
    purity = np.sum(np.max(contingency_matrix, axis=0)) / np.sum(contingency_matrix.values)

    # Calculate inverse purity (completeness)
    inv_purity = np.sum(np.max(contingency_matrix, axis=1)) / np.sum(contingency_matrix.values)

    # Calculate F1 measure
    f1 = 2 * (purity * inv_purity) / (purity + inv_purity) if (purity + inv_purity) > 0 else 0

    metrics = {
        'ARI': ari,
        'AMI': ami,
        'Purity': purity,
        'Inverse Purity': inv_purity,
        'F1': f1
    }

    print("\nClustering Evaluation Metrics:")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")

    return metrics