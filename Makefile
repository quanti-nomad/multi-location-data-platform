.PHONY: run fresh test clean

run:        ## incremental run: ingest new rows, rebuild, test, certify, report
	python pipeline.py

fresh:      ## rebuild the synthetic CRM and warehouse from scratch
	python pipeline.py --fresh

test:       ## end-to-end tests on a small isolated dataset
	pytest -q

clean:
	rm -rf data/*.sqlite data/*.duckdb transform/target transform/logs
