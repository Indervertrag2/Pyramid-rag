# Upload Pipeline Check - 2025-10-07 09:15:00 +02:00

- PDF ingestion now always routes through _extract_pdf_text, cascading PyMuPDF → pypdf before falling back to raw decoding. Warning metadata records when we have to use a fallback.
- Added regression test ackend/test_pdf_pipeline.py that uploads sample_docs/pipeline_test.pdf, asserts readable extraction, and simulates an LLM prompt containing the PDF text.
- Backend dependencies: pinned pypdf==6.1.1, added PyMuPDF==1.26.4, and removed the broken 	extract pin (bad metadata on current pip).
- Bumped 	orch to 2.7.1; for local installs on bare metal use pip install --extra-index-url https://download.pytorch.org/whl/cpu -r backend/requirements.txt so the PyTorch wheel resolves. Docker builds (Python 3.11) pick up the wheel automatically.
- Refreshing admin login: reset the admin hash to PyramidAdmin2024! after deployment so the default credentials work again.
- Restarted the full Docker stack with estart_all.bat; a browser hard refresh (Ctrl+Shift+R) is enough to pick up the new backend/frontend bundles.
