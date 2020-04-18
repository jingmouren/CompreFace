import itertools
import logging
import random
from collections import namedtuple

from sample_images import IMG_DIR
from sample_images.annotations import SAMPLE_IMAGES
from src.constants import ENV, LOGGING_LEVEL
from src.init_runtime import init_runtime
from src.services.facescan.optimize.optimizer import Optimizer
from src.services.facescan.optimize.results_storage import ResultsStorage
from src.services.facescan.scanner.facescanners import FaceScanners
from src.services.facescan.scanner.test.calculate_errors import calculate_errors
from src.services.imgtools.read_img import read_img
from src.services.utils.pyutils import get_dir, cached, Constants, get_env_split

CURRENT_DIR = get_dir(__file__)
Score = namedtuple('Score', 'cost args')

cached_read_img = cached(read_img)

ARG_COUNT = 4


class _ENV(Constants):
    LOGGING_LEVEL_NAME = ENV.LOGGING_LEVEL_NAME
    IMG_NAMES = get_env_split('IMG_NAMES', ' '.join([i.img_name for i in SAMPLE_IMAGES]))


class Facenet2018ThresholdOptimization:
    def __init__(self):
        self.scanner = FaceScanners.Facenet2018()
        self.dataset = [row for row in SAMPLE_IMAGES if row.img_name in _ENV.IMG_NAMES]
        logging.getLogger('src.services.facescan.scanner.test.calculate_errors').setLevel(logging.WARNING)
        logging.getLogger('src.services.facescan.scanner.facenet.facenet').setLevel(logging.INFO)

    def cost(self, new_x=None):
        if new_x:
            (self.scanner.det_prob_threshold,
             self.scanner.threshold_a,
             self.scanner.threshold_b,
             self.scanner.threshold_c) = tuple(new_x)

        total_errors = 0
        for row in self.dataset:
            img = cached_read_img(IMG_DIR / row.img_name)
            boxes = [face.box for face in self.scanner.scan(img)]
            errors = calculate_errors(boxes, row.noses)
            total_errors += errors
        return total_errors


def plausible_args_iterator():
    one_arg_values = [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]
    all_arg_values = list(itertools.product(one_arg_values, repeat=ARG_COUNT))
    random.shuffle(all_arg_values)
    return all_arg_values


def infinite_random_args_gen():
    while True:
        yield [random.uniform(0, 1) for _ in range(ARG_COUNT)]


if __name__ == '__main__':
    init_runtime(logging_level=LOGGING_LEVEL)
    logging.info(_ENV.to_json() if ENV.IS_DEV_ENV else _ENV.to_str())

    task = Facenet2018ThresholdOptimization()
    storage = ResultsStorage()
    optimizer = Optimizer(task, storage, checkpoint_every_s=120)

    optimizer.optimize(plausible_args_iterator())
    optimizer.optimize(infinite_random_args_gen())
