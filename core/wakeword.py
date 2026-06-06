"""
Custom Wake Word Detector
Uses OpenWakeWord embedding model + trained classifier.
"""

import json
import numpy as np
from pathlib import Path


class CustomWakeWordDetector:
    """Detect custom wake words using trained embeddings."""

    def __init__(self, model_path, threshold=0.5):
        self.threshold = threshold
        self.model_path = Path(model_path)

        # Load trained model
        with open(self.model_path, 'r') as f:
            data = json.load(f)

        self.wake_word = data['wake_word']
        self.weights = np.array(data['weights'])
        self.bias = np.array(data['bias'])
        self.scaler_mean = np.array(data['scaler_mean'])
        self.scaler_scale = np.array(data['scaler_scale'])

        # Load ONNX embedding model
        import onnxruntime as ort
        pkg_dir = Path(__file__).parent.parent
        import openwakeword
        oww_dir = Path(openwakeword.__file__).parent
        embedding_path = oww_dir / 'resources' / 'models' / 'embedding_model.onnx'

        self.session = ort.InferenceSession(str(embedding_path))
        self.input_name = self.session.get_inputs()[0].name

    def predict(self, audio, sample_rate=16000):
        """
        Predict if audio contains the wake word.

        Args:
            audio: numpy array of audio samples (float32)
            sample_rate: sample rate (default 16000)

        Returns:
            (is_wake_word: bool, confidence: float)
        """
        # Extract features
        from scipy.signal import stft
        f, t, Zxx = stft(audio, fs=sample_rate, nperseg=512, noverlap=352)
        magnitude = np.abs(Zxx)
        features = magnitude.T  # (time, freq)

        # Pad/truncate to expected shape (76, 32, 1)
        expected_frames = 76
        expected_features = 32

        if features.shape[0] < expected_frames:
            features = np.pad(features, ((0, expected_frames - features.shape[0]), (0, 0)))
        else:
            features = features[:expected_frames]

        if features.shape[1] < expected_features:
            features = np.pad(features, ((0, 0), (0, expected_features - features.shape[1])))
        else:
            features = features[:, :expected_features]

        features = features.reshape(1, expected_frames, expected_features, 1).astype(np.float32)

        # Get embedding
        embedding = self.session.run(None, {self.input_name: features})[0].flatten()

        # Scale
        scaled = (embedding - self.scaler_mean) / self.scaler_scale

        # Predict
        logit = np.dot(scaled, self.weights.flatten()) + self.bias[0]
        confidence = 1 / (1 + np.exp(-logit))  # sigmoid

        return confidence >= self.threshold, float(confidence)
