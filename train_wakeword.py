"""
Simple Custom Wake Word Trainer for OpenWakeWord
Records audio samples and trains a lightweight classifier.
"""

import sys
import os
import json
import time
import numpy as np
import sounddevice as sd
from pathlib import Path

# Fix encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass


SAMPLE_RATE = 16000
DURATION = 2  # seconds per sample
NUM_SAMPLES = 10  # number of positive samples to record
MODEL_DIR = Path(__file__).parent / "custom_wake_models"


def record_sample(duration=DURATION, sample_rate=SAMPLE_RATE):
    """Record a single audio sample."""
    print(f"  Recording {duration}s...", end="", flush=True)
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()
    print(" Done!")
    return audio.flatten()


def extract_embedding(audio, sample_rate=SAMPLE_RATE):
    """Extract embedding using OpenWakeWord's embedding model."""
    import onnxruntime as ort

    # Find the embedding model
    embedding_model_path = None
    pkg_dir = os.path.dirname(__import__('openwakeword').__file__)
    for root, dirs, files in os.walk(os.path.join(pkg_dir, 'resources')):
        for f in files:
            if f == 'embedding_model.onnx':
                embedding_model_path = os.path.join(root, f)
                break

    if not embedding_model_path:
        raise FileNotFoundError("Embedding model not found")

    # Load model
    session = ort.InferenceSession(embedding_model_path)
    input_name = session.get_inputs()[0].name
    input_shape = session.get_inputs()[0].shape
    print(f"    Model expects: {input_shape}")

    # Compute melspectrogram
    from scipy.signal import stft
    f, t, Zxx = stft(audio, fs=sample_rate, nperseg=512, noverlap=352)
    magnitude = np.abs(Zxx)

    # Get the right shape for the model
    features = magnitude.T  # (time, freq)

    # Model expects: (batch, 76, 32, 1)
    expected_frames = 76
    expected_features = 32

    # Truncate or pad time dimension
    if features.shape[0] < expected_frames:
        features = np.pad(features, ((0, expected_frames - features.shape[0]), (0, 0)))
    else:
        features = features[:expected_frames]

    # Truncate or pad feature dimension
    if features.shape[1] < expected_features:
        features = np.pad(features, ((0, 0), (0, expected_features - features.shape[1])))
    else:
        features = features[:, :expected_features]

    # Reshape to 4D: (batch, time, features, channel)
    features = features.reshape(1, expected_frames, expected_features, 1).astype(np.float32)

    # Run inference
    embedding = session.run(None, {input_name: features})[0]
    return embedding.flatten()


def train_classifier(embeddings, labels):
    """Train a simple classifier on embeddings."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X = scaler.fit_transform(embeddings)

    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(X, labels)

    return clf, scaler


def save_model(clf, scaler, wake_word, model_dir):
    """Save the trained model."""
    model_dir.mkdir(parents=True, exist_ok=True)

    # Save classifier weights
    model_data = {
        'weights': clf.coef_.tolist(),
        'bias': clf.intercept_.tolist(),
        'scaler_mean': scaler.mean_.tolist(),
        'scaler_scale': scaler.scale_.tolist(),
        'wake_word': wake_word,
    }

    model_path = model_dir / f"{wake_word.replace(' ', '_')}.json"
    with open(model_path, 'w') as f:
        json.dump(model_data, f)

    print(f"\nModel saved to: {model_path}")
    return model_path


def main():
    print("=" * 50)
    print("  Custom Wake Word Trainer")
    print("=" * 50)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--word', default='hi sans', help='Wake word to train')
    parser.add_argument('--samples', type=int, default=10, help='Number of samples')
    args = parser.parse_args()

    wake_word = args.word
    num_samples = args.samples

    print(f"\nWake word: '{wake_word}'")
    print(f"We'll record {num_samples} positive samples and generate negatives.\n")

    # Record positive samples
    print("=== Recording POSITIVE samples ===")
    print("Say the wake word clearly when you hear 'BEEP'.\n")

    positive_audio = []
    for i in range(num_samples):
        print(f"\n  Sample {i+1}/{num_samples}...")
        for countdown in range(3, 0, -1):
            print(f"  {countdown}...", end="", flush=True)
            time.sleep(1)
        print("  BEEP!", flush=True)
        # Short beep
        try:
            import winsound
            winsound.Beep(1000, 200)
        except:
            pass
        audio = record_sample()
        positive_audio.append(audio)

    # Generate negative samples (silence + random noise)
    print("\n=== Generating NEGATIVE samples ===")
    negative_audio = []
    for i in range(num_samples * 2):
        # Random background noise
        noise = np.random.randn(SAMPLE_RATE * DURATION) * 0.01
        negative_audio.append(noise)

    # Extract embeddings
    print("\n=== Extracting features ===")
    all_embeddings = []
    all_labels = []

    for i, audio in enumerate(positive_audio):
        print(f"  Positive sample {i+1}/{len(positive_audio)}...")
        emb = extract_embedding(audio)
        all_embeddings.append(emb)
        all_labels.append(1)

    for i, audio in enumerate(negative_audio):
        print(f"  Negative sample {i+1}/{len(negative_audio)}...")
        emb = extract_embedding(audio)
        all_embeddings.append(emb)
        all_labels.append(0)

    # Train classifier
    print("\n=== Training classifier ===")
    X = np.array(all_embeddings)
    y = np.array(all_labels)

    clf, scaler = train_classifier(X, y)

    # Test accuracy
    X_scaled = scaler.transform(X)
    predictions = clf.predict(X_scaled)
    accuracy = np.mean(predictions == y)
    print(f"  Training accuracy: {accuracy*100:.1f}%")

    # Save model
    save_model(clf, scaler, wake_word, MODEL_DIR)

    print("\n=== Done! ===")
    print(f"Model trained for wake word: '{wake_word}'")
    print(f"Use it in your voice assistant by loading the model file.")


if __name__ == "__main__":
    main()
