import os
import json

class Logger:
    def __init__(self, config):
        self.config = config
        self.outputs_path = config['paths']['outputs']
        os.makedirs(self.outputs_path, exist_ok=True)

    def save_detection_json(self, result):
        filename = self.config['output_files'].get('detection_result_json', 'detection_result.json')
        path = os.path.join(self.outputs_path, filename)
        with open(path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Detection JSON saved to {path}")
        return path
