"""
Bird Species Prediction Script

This script predicts bird species from audio files using the trained model.
"""

import datetime
import os

def log_debug(message):
    """Log a debug message to a file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("analysis_debug.log", "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass
    print(f"DEBUG: {message}")

log_debug("Starting imports...")
import numpy as np
log_debug("numpy imported")
import pandas as pd
log_debug("pandas imported")
from librosa import feature
log_debug("librosa.feature imported")
import soundfile as sf
log_debug("soundfile imported")
import pickle
log_debug("pickle imported")

# Set Numba cache to a local directory to avoid permission hangs on Windows
os.environ['NUMBA_CACHE_DIR'] = os.path.join(os.getcwd(), 'tmp', 'numba_cache')
if not os.path.exists(os.path.join(os.getcwd(), 'tmp', 'numba_cache')):
    os.makedirs(os.path.join(os.getcwd(), 'tmp', 'numba_cache'), exist_ok=True)

log_debug("Starting sklearn import...")
from sklearn import naive_bayes
log_debug("sklearn.naive_bayes imported")
import datetime

def log_debug(message):
    """Log a debug message to a file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("analysis_debug.log", "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"DEBUG: {message}")



def extract_features_from_audio(audio_file_path, window_size=6144, sample_rate=22050):
    """
    Extract audio features from a bird song recording.
    
    Args:
        audio_file_path: Path to the audio file (.flac, .wav, etc.)
        window_size: Size of each window in samples (default: 6144)
        sample_rate: Sample rate for audio processing
    
    Returns:
        DataFrame with extracted features
    """
    print(f"Loading audio file: {audio_file_path}")
    
    # Load audio file, downmixing to mono and resampling to target sample rate
    log_debug(f"Starting audio load: {audio_file_path}")
    import librosa
    try:
        data, sr = librosa.load(audio_file_path, sr=sample_rate, mono=True)
        log_debug(f"Audio loaded successfully: {len(data)} samples at {sr} Hz")
    except Exception as e:
        log_debug(f"CRITICAL ERROR during librosa.load: {str(e)}")
        raise

    
    print(f"Audio loaded: {len(data)} samples at {sr} Hz")
    print(f"Duration: {len(data)/sr:.2f} seconds")
    
    features_list = []
    
    # Process each window in the audio
    num_windows = max(1, len(data) // window_size)
    print(f"Processing {num_windows} windows...")
    
    for i in range(0, min(len(data), num_windows * window_size), window_size):
        if i + window_size > len(data):
            break
            
        window = data[i:i+window_size]
        
        # log_debug(f"Processing window {i//window_size}")
        # Extract spectral centroid (13 values)

        spec_centroid = feature.spectral_centroid(y=window, sr=sr)[0]
        
        # Extract chromagram (12 pitch classes × 13 time frames)
        chroma = feature.chroma_stft(y=window, sr=sr)
        
        # Build feature vector
        feature_vector = {}
        for j in range(0, 13):
            feature_vector[f'spec_centr_{j}'] = spec_centroid[j] if j < len(spec_centroid) else 0
            for k in range(0, 12):
                feature_vector[f'chromogram_{k}_{j}'] = chroma[k, j]
        
        features_list.append(feature_vector)
    
    return pd.DataFrame(features_list)


def predict_species(model, audio_file_path, species_names=None):
    """
    Predict bird species from an audio file.
    
    Args:
        model: Trained classifier (e.g., Naive Bayes)
        audio_file_path: Path to the audio file
        species_names: List of species names (optional)
    
    Returns:
        Dictionary with prediction results
    """
    # Extract features
    features_df = extract_features_from_audio(audio_file_path)
    
    # Get feature columns (exclude species and genus if present)
    feature_columns = [col for col in features_df.columns 
                      if col not in ['species', 'genus']]
    
    X_new = features_df[feature_columns].values
    
    # Make predictions
    predictions = model.predict(X_new)
    prediction_probs = model.predict_proba(X_new)
    
    # Aggregate predictions (majority vote)
    unique, counts = np.unique(predictions, return_counts=True)
    most_common_species = unique[np.argmax(counts)]
    confidence = max(counts) / len(predictions) * 100
    
    # Get average probabilities for each class
    avg_probs = np.mean(prediction_probs, axis=0)
    
    results = {
        'predicted_species': most_common_species,
        'confidence': confidence,
        'num_windows': len(predictions),
        'window_predictions': predictions.tolist(),
        'class_probabilities': {
            model.classes_[i]: avg_probs[i] * 100 
            for i in range(len(model.classes_))
        }
    }
    
    return results


def main():
    """
    Example usage of the prediction script.
    """
    # Load the trained model
    # Option 1: If you saved the model
    # with open('bird_classifier_model.pkl', 'rb') as f:
    #     model = pickle.load(f)
    
    # Option 2: Train a new model from the CSV files
    print("Loading training data...")
    train_data = pd.read_csv("train.csv")
    
    # Prepare features and labels
    features = [col for col in train_data.columns 
               if col not in ['species', 'genus', 'Unnamed: 0']]
    
    X_train = train_data[features].values
    y_train = train_data['species'].values
    
    # Train Naive Bayes classifier
    print("Training Naive Bayes classifier...")
    model = naive_bayes.GaussianNB()
    model.fit(X_train, y_train)
    print(f"Model trained on {len(X_train)} samples")
    print(f"Species classes: {model.classes_}")
    
    # Save the model for future use
    print("\nSaving model...")
    with open('bird_classifier_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    print("Model saved to 'bird_classifier_model.pkl'")
    
    # Example: Predict on a test audio file
    print("\n" + "="*60)
    print("PREDICTION EXAMPLE")
    print("="*60)
    
    # You can specify your own audio file here
    test_audio = "songs/xc132608.flac"  # Replace with your audio file
    
    try:
        results = predict_species(model, test_audio)
        
        print(f"\n🐦 PREDICTION RESULTS:")
        print(f"  Predicted Species: {results['predicted_species']}")
        print(f"  Confidence: {results['confidence']:.2f}%")
        print(f"  Windows Analyzed: {results['num_windows']}")
        
        print(f"\n  Class Probabilities:")
        for species, prob in sorted(results['class_probabilities'].items(), 
                                   key=lambda x: x[1], reverse=True):
            print(f"    {species}: {prob:.2f}%")
            
    except FileNotFoundError:
        print(f"\n⚠️  Audio file not found: {test_audio}")
        print("Please provide a valid audio file path.")


if __name__ == "__main__":
    main()