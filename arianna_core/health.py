import os
import json
from . import mini_le
from . import memory


def health_status():
    status = {
        "model_exists": os.path.exists(mini_le.MODEL_FILE),
        "log_size": os.path.getsize(mini_le.LOG_FILE) if os.path.exists(mini_le.LOG_FILE) else 0,
        "human_log_size": os.path.getsize(mini_le.HUMAN_LOG) if os.path.exists(mini_le.HUMAN_LOG) else 0,
    }
    model = mini_le.load_model()
    sample = mini_le.generate(model, length=20) if model else ""
    status["sample_quality"] = len(sample)
    status["top_patterns"] = memory.top_patterns()
    return status


if __name__ == "__main__":
    print(json.dumps(health_status()))
