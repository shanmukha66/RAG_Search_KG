import unittest
import os
from pathlib import Path
import tempfile
import shutil
from ingestion.pipeline import IngestionPipeline
from ingestion.audio.processor import AudioProcessor
from ingestion.video.processor import VideoProcessor

class TestIngestionPipeline(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.pipeline = IngestionPipeline(output_dir=os.path.join(self.test_dir, "output"))
        
        # Create test files
        self.create_test_files()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
        
    def create_test_files(self):
        """Create test files for different media types"""
        # Create a simple audio file (1 second of silence)
        from pydub import AudioSegment
        audio = AudioSegment.silent(duration=1000)  # 1 second
        self.test_audio = os.path.join(self.test_dir, "test.wav")
        audio.export(self.test_audio, format="wav")
        
        # Create a simple video file (1 second of black frames)
        import cv2
        import numpy as np
        self.test_video = os.path.join(self.test_dir, "test.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.test_video, fourcc, 30.0, (640,480))
        for _ in range(30):  # 1 second at 30 fps
            frame = np.zeros((480,640,3), np.uint8)
            out.write(frame)
        out.release()
        
        # Create a test text file
        self.test_text = os.path.join(self.test_dir, "test.txt")
        with open(self.test_text, 'w') as f:
            f.write("This is a test document.")
            
    def test_file_type_detection(self):
        """Test file type detection"""
        self.assertEqual(self.pipeline.detect_file_type(self.test_audio), 'audio')
        self.assertEqual(self.pipeline.detect_file_type(self.test_video), 'video')
        self.assertEqual(self.pipeline.detect_file_type(self.test_text), 'text')
        
    def test_audio_processing(self):
        """Test audio processing"""
        result = self.pipeline.process_file(self.test_audio)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['file_type'], 'audio')
        self.assertTrue(os.path.exists(result['output_path']))
        
    def test_video_processing(self):
        """Test video processing"""
        result = self.pipeline.process_file(self.test_video)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['file_type'], 'video')
        self.assertTrue(os.path.exists(result['output_path']))
        
    def test_batch_processing(self):
        """Test batch processing"""
        files = [self.test_audio, self.test_video, self.test_text]
        results = self.pipeline.process_batch(files)
        
        self.assertEqual(len(results), 3)
        success_count = sum(1 for r in results if r['status'] == 'success')
        self.assertGreaterEqual(success_count, 2)  # At least audio and video should succeed
        
    def test_audio_processor(self):
        """Test audio processor specifically"""
        processor = AudioProcessor()
        result = processor.transcribe(self.test_audio)
        self.assertIn('text', result)
        self.assertIn('segments', result)
        
    def test_video_processor(self):
        """Test video processor specifically"""
        processor = VideoProcessor()
        frames = processor.extract_frames(self.test_video)
        self.assertGreater(len(frames['frames']), 0)
        self.assertEqual(len(frames['frames']), len(frames['timestamps']))
        
if __name__ == '__main__':
    unittest.main() 