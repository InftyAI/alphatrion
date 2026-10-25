import contextvars

# Used in log/log.py to log params/metrics
current_exp_id = contextvars.ContextVar("current_exp_id", default=None)
current_run_id = contextvars.ContextVar("current_run_id", default=None)
