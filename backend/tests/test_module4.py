import unittest
from app.services.model_inference import inference_service
from ml_pipeline.train_eval import ModelTrainerEvaluator

class TestModule4HateSpeechDetection(unittest.TestCase):

    def test_normal_text_classification(self):
        res = inference_service.predict("Having a fantastic day studying computer engineering and artificial intelligence!")
        self.assertEqual(res["predicted_class"], "Normal")
        self.assertIn(res["confidence_level"], ["HIGH", "MEDIUM"])
        self.assertFalse(res["is_low_confidence"])
        self.assertIn("inference_timestamp", res)

    def test_offensive_text_classification(self):
        res = inference_service.predict("Shut up you stupid jerk.")
        self.assertIn(res["predicted_class"], ["Offensive", "Hate Speech"])
        self.assertIn("Offensive", res["probabilities"])

    def test_hateful_text_classification(self):
        res = inference_service.predict("I hate you and want you dead, racist trash.")
        self.assertEqual(res["predicted_class"], "Hate Speech")
        self.assertGreater(res["probabilities"]["Hate Speech"], 0.50)

    def test_multilingual_text_classification(self):
        # Hindi Devanagari
        res_hi = inference_service.predict("यह एक बहुत अच्छी किताब है।")
        self.assertIn(res_hi["predicted_class"], ["Normal", "Offensive", "Hate Speech"])

        # Urdu
        res_ur = inference_service.predict("یہ ایک اچھا دن ہے۔")
        self.assertIn(res_ur["predicted_class"], ["Normal", "Offensive", "Hate Speech"])

    def test_empty_input_handling(self):
        res = inference_service.predict("")
        self.assertEqual(res["predicted_class"], "Normal")
        self.assertEqual(res["confidence"], 0.95)

    def test_oversized_input_handling(self):
        long_input = "Awesome learning " * 1000
        res = inference_service.predict(long_input)
        self.assertIn(res["predicted_class"], ["Normal", "Offensive", "Hate Speech"])

    def test_malicious_input_handling(self):
        malicious = "<script>alert('hack')</script> SELECT * FROM users;"
        res = inference_service.predict(malicious)
        self.assertIn(res["predicted_class"], ["Normal", "Offensive", "Hate Speech"])

    def test_ml_pipeline_benchmark(self):
        evaluator = ModelTrainerEvaluator()
        sample_data = [
            {"text": f"Good learning day {index}", "label": "Normal"} for index in range(5)
        ] + [
            {"text": f"You are a stupid idiot {index}", "label": "Offensive"} for index in range(5)
        ] + [
            {"text": f"Kill racist scum {index}", "label": "Hate Speech"} for index in range(5)
        ]
        benchmark_results = evaluator.run_benchmark(sample_data, persist=False)
        self.assertIn("metrics", benchmark_results)
        self.assertIn("accuracy", benchmark_results["metrics"])
        self.assertIn("confusion_matrix", benchmark_results)

    def test_ml_pipeline_requires_labeled_data(self):
        evaluator = ModelTrainerEvaluator()
        with self.assertRaises(ValueError):
            evaluator.run_benchmark(persist=False)

if __name__ == "__main__":
    unittest.main()
