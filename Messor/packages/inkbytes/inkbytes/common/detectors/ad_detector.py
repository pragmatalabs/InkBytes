import logging
import numpy as np
import pandas as pd
import os
import datetime
from typing import List, Dict, Union, Any
from pathlib import Path
import joblib
from tinydb import TinyDB, Query
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

class AdvertisementDetector:
    """
    A class for detecting advertisements in articles using a pre-trained model.
    
    This detector can load a trained model from a file and use it to predict whether
    articles contain advertisements. It supports both sklearn Pipeline models and
    other compatible model formats.
    """
    
    def __init__(self, model_path: Union[str, Path], threshold: float = 0.5):
        """
        Initialize the advertisement detector with a model.
        
        Args:
            model_path: Path to the trained model file (.joblib, .pkl, etc.)
            threshold: Probability threshold for classifying text as an advertisement (default: 0.5)
        """
        self.model_path = Path(model_path) if isinstance(model_path, str) else model_path
        self.threshold = threshold
        self.model = self._load_model()
        logger.info(f"Advertisement detector initialized with model from {model_path}")
    
    def _load_model(self):
        """Load the trained model from the specified path."""
        try:
            logger.info(f"Loading advertisement detection model from {self.model_path}")
            model = joblib.load(self.model_path)
            logger.info(f"Model loaded successfully: {type(model)}")
            return model
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def predict(self, texts: List[str]) -> List[bool]:
        """
        Predict whether each text contains an advertisement.
        
        Args:
            texts: List of article texts to classify
            
        Returns:
            List of boolean values where True indicates an advertisement
        """
        if not texts:
            return []
        
        try:
            # Handle different types of model outputs (binary vs probability)
            if hasattr(self.model, 'predict_proba'):
                # Get probability scores for the positive class
                proba = self.model.predict_proba(texts)
                # If it's a binary classification, get the probabilities for class 1
                if proba.shape[1] == 2:
                    ad_scores = proba[:, 1]
                else:
                    ad_scores = proba.flatten()
                # Apply threshold
                predictions = ad_scores >= self.threshold
            else:
                # Direct binary predictions
                predictions = self.model.predict(texts)
                
            return predictions.tolist()
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            # Return False (not an ad) for all texts on error
            return [False] * len(texts)
    
    def filter_advertisements(self, df: pd.DataFrame, text_column: str = 'text') -> pd.DataFrame:
        """
        Filter out articles that are classified as advertisements.
        
        Args:
            df: DataFrame containing articles
            text_column: Name of the column containing article text
            
        Returns:
            DataFrame with advertisements removed
        """
        if df.empty:
            return df
        
        # Ensure text column exists and has valid values
        if text_column not in df.columns:
            logger.warning(f"Text column '{text_column}' not found in DataFrame. Returning original DataFrame.")
            return df
        
        # Fill NaN values with empty strings
        df[text_column] = df[text_column].fillna('')
        
        # Get predictions for each article
        texts = df[text_column].tolist()
        is_advertisement = self.predict(texts)
        
        # Create a copy of ads that are being filtered out
        ad_df = df[np.array(is_advertisement)].copy()
        if not ad_df.empty:
            self._save_filtered_ads(ad_df)
        
        # Filter out advertisements
        non_ad_df = df[~np.array(is_advertisement)]
        
        # Log statistics
        total_articles = len(df)
        retained_articles = len(non_ad_df)
        filtered_articles = total_articles - retained_articles
        
        logger.info(f"Advertisement filtering: {filtered_articles} ads removed out of {total_articles} articles ({filtered_articles/total_articles:.1%})")
        
        return non_ad_df
    
    def _save_filtered_ads(self, ad_df: pd.DataFrame):
        """
        Save information about filtered advertisements to a TinyDB JSON file.
        
        Args:
            ad_df: DataFrame containing filtered advertisement articles
        """
        try:
            # Ensure directory exists
            filtered_dir = Path('staging/filtered')
            filtered_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            output_file = filtered_dir / f'filtered_advertisements_{timestamp}.tdb.json'
            
            # Create TinyDB instance
            db = TinyDB(output_file)
            
            # Extract only needed fields for each advertisement
            ad_records = []
            
            for _, row in ad_df.iterrows():
                record = {}
                
                # Get unique identifier
                if 'uid' in row:
                    record['uid'] = row['uid']
                elif 'id' in row:
                    record['uid'] = row['id']
                else:
                    # Skip records without an identifier
                    continue
                
                # Get title
                if 'title' in row:
                    record['title'] = row['title']
                else:
                    # Skip records without a title
                    continue
                
                # Get summary
                if 'summary' in row:
                    record['summary'] = row['summary']
                elif 'description' in row:
                    record['summary'] = row['description']
                else:
                    record['summary'] = ""
                
                ad_records.append(record)
            
            if not ad_records:
                logger.warning("No valid advertisement records to save.")
                return
            
            # Save to TinyDB
            db.insert_multiple(ad_records)
            logger.info(f"Saved {len(ad_records)} filtered advertisements to {output_file}")
                
        except Exception as e:
            logger.error(f"Error saving filtered advertisements: {str(e)}")


def create_detector(model_path: Union[str, Path], threshold: float = 0.5) -> AdvertisementDetector:
    """
    Create an AdvertisementDetector instance.
    
    Args:
        model_path: Path to the trained model file
        threshold: Probability threshold for classifying as advertisement
        
    Returns:
        Configured AdvertisementDetector instance
    """
    return AdvertisementDetector(model_path=model_path, threshold=threshold)