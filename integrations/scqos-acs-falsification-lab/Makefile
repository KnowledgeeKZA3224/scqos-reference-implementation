.PHONY: bootstrap test verify live
bootstrap:
	./scripts/bootstrap.sh

test:
	. .venv/bin/activate && pytest -q

verify:
	./scripts/verify-everything.sh

live:
	LIVE_SCQOS=1 ./scripts/verify-everything.sh
