from old.abuse_cnn_meta_model import AbuseCNNMetaModel
from old.abuse_meta_model import AbuseMetaModel
from old.pos_meta_model import POSMetaModel
from torch import optim

import coloredlogs
import logging
import os
import torch

logger = logging.getLogger('MetaLearningLog')
coloredlogs.install(logger=logger, level='DEBUG',
                    fmt='%(asctime)s - %(name)s - %(levelname)s'
                        ' - %(message)s')


class MetaLearning:
    def __init__(self, config):
        self.base = config['base']
        self.stamp = config['stamp']
        self.updates = config['num_updates']
        self.meta_epochs = config['num_meta_epochs']
        self.early_stopping = config['early_stopping']
        self.meta_lr = config.get('meta_lr', 1e-3)
        self.meta_weight_decay = config.get('meta_weight_decay', 0.0)
        if 'pos' in config['meta_model']:
            self.meta_model = POSMetaModel(config)
        if 'abuse_meta' in config['meta_model']:
            self.meta_model = AbuseMetaModel(config)
        if 'abuse_cnn_meta' in config['meta_model']:
            self.meta_model = AbuseCNNMetaModel(config)
        logger.info('Meta learner instantiated')

    def training(self, support_loaders, query_loaders, identifiers):
        meta_optimizer = optim.Adam(
            self.meta_model.learner.parameters(), lr=self.meta_lr,
            weight_decay=self.meta_weight_decay
        )
        best_loss = float('inf')
        patience = 0
        model_path = os.path.join(
            self.base, 'saved_models', 'MetaModel-{}.h5'.format(self.stamp)
        )
        for epoch in range(self.meta_epochs):
            meta_optimizer.zero_grad()
            losses, accuracies = self.meta_model(
                support_loaders, query_loaders, identifiers, self.updates
            )
            meta_optimizer.step()

            loss_value = torch.mean(torch.Tensor(losses)).item()
            accuracy = sum(accuracies) / len(accuracies)
            logger.info('Meta epoch {}:\tavg loss={:.5f}\tavg accuracy={:.5f}'.format(
                epoch + 1, loss_value, accuracy
            ))
            if loss_value <= best_loss:
                patience = 0
                best_loss = loss_value
                torch.save(self.meta_model.learner.state_dict(), model_path)
                logger.info('Saving the model since the loss improved')
                logger.info('')
            else:
                patience += 1
                logger.info('Loss did not improve')
                logger.info('')
                if patience == self.early_stopping:
                    break
        self.meta_model.learner.load_state_dict(torch.load(model_path))

    def testing(self, support_loaders, query_loaders, identifiers):
        logger.info('---------- Meta testing starts here ----------')
        for support, query, idx in zip(
                support_loaders, query_loaders, identifiers
        ):
            self.meta_model([support], [query], [idx], self.updates+10)
            logger.info('')