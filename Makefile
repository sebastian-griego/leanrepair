.PHONY: dev test verify verify-report snapshot snapshot-check source-hashes

PYTHON ?= python
SNAPSHOT_ROOT ?= results/real_paper_v2
SNAPSHOT_JSON ?= $(SNAPSHOT_ROOT)/snapshot_summary.json
REPRO_REPORT ?= results/reproducibility_report.json

dev:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest -q

verify:
	$(PYTHON) scripts/verify_reproducibility.py

verify-report:
	$(PYTHON) scripts/verify_reproducibility.py --report-json $(REPRO_REPORT)

snapshot:
	$(PYTHON) scripts/summarize_real_paper_snapshot.py --root $(SNAPSHOT_ROOT)

snapshot-check:
	$(PYTHON) scripts/summarize_real_paper_snapshot.py --root $(SNAPSHOT_ROOT) --check

source-hashes:
	$(PYTHON) scripts/summarize_real_paper_snapshot.py \
	  --output-json $(SNAPSHOT_JSON) \
	  --verify-source-hashes
