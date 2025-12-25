# Makefile

#跑线上审计 (检查历史):
eval-audit:
	python -m evaluation.pipelines.audit_online

#跑回归测试 (测试 Dataset)
eval-test:
	python -m evaluation.pipelines.test_dataset

# 调试某条 Trace:
debug:
	python -m evaluation.tools.inspect_trace