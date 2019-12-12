import random

from torch.utils import data

from datasets.episode import Episode


def get_max_batch_len(batch):
    return max([len(x[0]) for x in batch])


def prepare_batch(batch):
    max_len = get_max_batch_len(batch)
    x = []
    lengths = []
    y = []
    for inp_seq, target_seq in batch:
        lengths.append(len(inp_seq))
        inp_seq = inp_seq + ['<PAD>'] * (max_len - len(inp_seq))
        target_seq = target_seq + [-1] * (max_len - len(target_seq))
        x.append(inp_seq)
        y.append(target_seq)
    return x, lengths, y


def generate_episodes_from_split_datasets(train_dataset, test_dataset, n_episodes, n_support_examples, n_query_examples, task):
    if n_episodes * n_support_examples > train_dataset.__len__() or n_episodes * n_query_examples > test_dataset.__len__():
        raise Exception('Unable to balance the dataset correctly')

    train_indices = list(range(train_dataset.__len__()))
    random.shuffle(train_indices)

    test_indices = list(range(test_dataset.__len__()))
    random.shuffle(test_indices)

    train_start_index, test_start_index = 0, 0
    episodes = []
    for e in range(n_episodes):
        train_subset = data.Subset(train_dataset, train_indices[train_start_index: train_start_index + n_support_examples])
        support_loader = data.DataLoader(train_subset, batch_size=n_support_examples, collate_fn=prepare_batch)
        train_start_index += n_support_examples
        test_subset = data.Subset(test_dataset, test_indices[test_start_index: test_start_index + n_query_examples])
        query_loader = data.DataLoader(test_subset, batch_size=n_query_examples, collate_fn=prepare_batch)
        test_start_index += n_query_examples
        episode = Episode(support_loader, query_loader, task)
        episodes.append(episode)
    return episodes


def generate_episodes_from_single_dataset(dataset, n_episodes, n_support_examples, n_query_examples, task):
    if n_episodes * (n_support_examples + n_query_examples) > dataset.__len__():
        raise Exception('Unable to balance the dataset correctly')

    indices = list(range(dataset.__len__()))
    random.shuffle(indices)

    start_index = 0
    episodes = []
    for e in range(n_episodes):
        train_subset = data.Subset(dataset, indices[start_index: start_index + n_support_examples])
        support_loader = data.DataLoader(train_subset, batch_size=n_support_examples, collate_fn=prepare_batch)
        start_index += n_support_examples
        test_subset = data.Subset(dataset, indices[start_index: start_index + n_query_examples])
        query_loader = data.DataLoader(test_subset, batch_size=n_query_examples, collate_fn=prepare_batch)
        start_index += n_query_examples
        episode = Episode(support_loader, query_loader, task)
        episodes.append(episode)
    return episodes


def generate_full_query_episode(train_dataset, test_dataset, n_support_examples, task, batch_size=32):
    train_indices = list(range(train_dataset.__len__()))
    random.shuffle(train_indices)
    train_subset = data.Subset(train_dataset, train_indices[0:n_support_examples])
    support_loader = data.DataLoader(train_subset, batch_size=n_support_examples, collate_fn=prepare_batch)
    query_loader = data.DataLoader(test_dataset, batch_size=batch_size, collate_fn=prepare_batch)
    episode = Episode(support_loader, query_loader, task)
    return [episode]