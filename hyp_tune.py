import logging
import os
import random
from argparse import ArgumentParser

import coloredlogs
import yaml
import numpy as np

from datetime import datetime

from datasets import utils
from datasets.wsd_dataset import WSDDataset
from models.baseline import Baseline
from models.majority_classifier import MajorityClassifier
from models.maml import MAML
from models.proto_network import PrototypicalNetwork


logger = logging.getLogger('MetaLearningLog')
coloredlogs.install(logger=logger, level='DEBUG',
                    fmt='%(asctime)s - %(name)s - %(levelname)s'
                        ' - %(message)s')


def load_config(config_file):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    config['base_path'] = os.path.dirname(os.path.abspath(__file__))
    config['stamp'] = str(datetime.now()).replace(':', '-').replace(' ', '_')
    return config


def train(config):
    # Path for WSD dataset
    wsd_base_path = os.path.join(config['base_path'], '../data/word_sense_disambigation_corpora/semcor/')

    # Load WSD dataset
    logger.info('Loading the dataset for WSD')
    wsd_dataset = WSDDataset(wsd_base_path)
    logger.info('Finished loading the dataset for WSD')

    # Generate episodes for WSD
    logger.info('Generating episodes for WSD')
    wsd_episodes = utils.generate_wsd_episodes(wsd_dataset=wsd_dataset,
                                               n_episodes=config['num_episodes']['wsd'],
                                               n_support_examples=config['num_shots']['wsd'],
                                               n_query_examples=config['num_test_samples']['wsd'],
                                               task='wsd')
    random.shuffle(wsd_episodes)
    logger.info('Finished generating episodes for WSD')

    # Initialize meta learner
    if config['meta_learner'] == 'maml':
        meta_learner = MAML(config)
    elif config['meta_learner'] == 'proto_net':
        meta_learner = PrototypicalNetwork(config)
    elif config['meta_learner'] == 'baseline':
        meta_learner = Baseline(config)
    elif config['meta_learner'] == 'majority':
        meta_learner = MajorityClassifier()
    else:
        raise NotImplementedError

    # Meta-training
    avg_f1 = meta_learner.training(wsd_episodes[:-50])
    return avg_f1


if __name__ == '__main__':

    # Parse arguments
    parser = ArgumentParser()
    parser.add_argument('--config', dest='config_file', type=str, help='Configuration file', required=True)
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config_file)

    # Directory for saving models
    os.makedirs(os.path.join(config['base_path'], 'saved_models'), exist_ok=True)
    
    for learner_lr in [1, 0.5, 0.01]:
        for meta_lr in [1, 0.5, 0.01]:
            for hidden_size in [64, 128, 256]:
                for num_updates in [3, 5]:
                    f1s = []
                    config['learner_params']['hidden_size'] = hidden_size
                    config['learner_lr'] = learner_lr
                    config['meta_lr'] = meta_lr
                    config['num_updates'] = num_updates
                    logger.info('Using configuration: {}'.format(config))
                    for i in range(3):
                        f1 = train(config)
                        f1s.append(f1)
                    avg_f1 = np.mean(f1)
                    logger.info('Got average F1: {}', avg_f1)
                    if avg_f1 > best_f1:
                        best_config = config
                        best_f1 = avg_f1

    logger.info('Tuning finished with best F1 score of {}'.format(best_f1))
    logger.info('Best config: {}'.format(best_config))
