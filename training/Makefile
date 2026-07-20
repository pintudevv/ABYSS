# ABYSS - Model Retraining Commands
# Run from training/ directory

# 1. Vectorize EMBER 2018 dataset (if JSONL files exist)
vectorize:
	python vectorize_sample.py --train-samples 60000 --test-samples 3000

# 2. Train models (Random Forest, XGBoost, Autoencoder)
train:
	python train_model.py

# 3. Generate model manifest (SHA256 hashes for integrity check)
manifest:
	python generate_manifest.py

# 4. Full retrain pipeline (vectorize + train + manifest)
retrain: vectorize train manifest
	@echo "Retraining complete. Models saved to ../backend/models/"

# 5. Test on custom sample
test-custom:
	python build_test_sample.py
	python test_custom_sample.py

# 6. Test on real malware (downloads WannaCry)
test-malware:
	python test_malware.py

.PHONY: vectorize train manifest retrain test-custom test-malware