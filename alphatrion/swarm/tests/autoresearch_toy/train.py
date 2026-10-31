"""
A tiny CPU stand-in for autoresearch's train.py, to test the pipeline
without a GPU: it fits y = sin(3x) with a polynomial by gradient descent,
and reports the validation loss as val_bpb. Too high a learning rate
diverges, which crashes the run.
"""

import math
import random

LR = 0.05
STEPS = 300
DEGREE = 3
SEED = 0

random.seed(SEED)
train = [(x, math.sin(3 * x)) for x in (random.uniform(-1, 1) for _ in range(200))]
valid = [(x, math.sin(3 * x)) for x in (random.uniform(-1, 1) for _ in range(100))]
weights = [0.0] * (DEGREE + 1)


def predict(x):
    return sum(w * x**k for k, w in enumerate(weights))


def loss(data):
    return sum((predict(x) - y) ** 2 for x, y in data) / len(data)


for _ in range(STEPS):
    grads = [0.0] * len(weights)
    for x, y in train:
        error = predict(x) - y
        for k in range(len(weights)):
            grads[k] += 2 * error * x**k / len(train)
    weights = [w - LR * g for w, g in zip(weights, grads, strict=True)]

val_loss = loss(valid)
if not math.isfinite(val_loss):
    raise SystemExit("training diverged")
print(f"val_bpb: {val_loss:.6f}")
print("peak_vram_mb: 0.0")
